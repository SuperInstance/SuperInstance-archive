"""
Future Needs Predictor - Predicts what users will need before they know it.
Examples: "User will need tax docs in March", "Vacation planning in June", etc.
Uses temporal patterns, life event detection, and predictive modeling.
"""

import asyncio
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import calendar
from collections import defaultdict, deque
import numpy as np

class PredictionType(Enum):
    DOCUMENT_NEED = "document_need"
    PLANNING_NEED = "planning_need"
    COMPLIANCE_NEED = "compliance_need"
    LIFE_EVENT = "life_event"
    SEASONAL_NEED = "seasonal_need"
    ANNIVERSARY_REMINDER = "anniversary_reminder"

class Urgency(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Certainty(Enum):
    POSSIBLE = "possible"      # 30-50%
    LIKELY = "likely"          # 50-75%
    VERY_LIKELY = "very_likely" # 75-90%
    CERTAIN = "certain"        # 90%+

@dataclass
class FutureNeed:
    """Predicted future need."""
    prediction_id: str
    user_id: str
    need_type: PredictionType
    title: str
    description: str
    predicted_date: datetime
    urgency: Urgency
    certainty: Certainty
    context: Dict[str, Any]
    recommended_actions: List[str]
    related_files: List[str]
    created_at: datetime
    expires_at: datetime

@dataclass
class LifeEvent:
    """Detected or predicted life event."""
    event_id: str
    user_id: str
    event_type: str
    event_name: str
    predicted_date: datetime
    confidence: float
    triggers: List[str]
    implications: List[str]

class TemporalPatternDetector:
    """Detects temporal patterns and seasonal needs."""
    
    def __init__(self):
        self.seasonal_patterns = self._load_seasonal_patterns()
        self.compliance_calendar = self._load_compliance_calendar()
        self.life_event_patterns = self._load_life_event_patterns()
    
    def _load_seasonal_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load seasonal and recurring patterns."""
        return {
            "tax_season": {
                "peak_months": [3, 4],  # March-April
                "preparation_months": [1, 2],  # January-February
                "documents_needed": ["W2", "1099", "receipts", "tax_returns", "bank_statements"],
                "typical_actions": ["gather_documents", "find_accountant", "prepare_returns"],
                "urgency_curve": {1: "low", 2: "medium", 3: "high", 4: "critical"}
            },
            "vacation_planning": {
                "peak_months": [6, 7, 8, 12],  # Summer and holidays
                "preparation_months": [4, 5, 10, 11],
                "documents_needed": ["passport", "travel_insurance", "itinerary", "bookings"],
                "typical_actions": ["book_flights", "reserve_hotels", "plan_activities"],
                "urgency_curve": {4: "low", 5: "medium", 6: "high"}
            },
            "back_to_school": {
                "peak_months": [8, 9],
                "preparation_months": [6, 7],
                "documents_needed": ["transcripts", "applications", "financial_aid", "supplies_list"],
                "typical_actions": ["register_classes", "buy_supplies", "arrange_housing"],
                "urgency_curve": {6: "low", 7: "medium", 8: "high", 9: "critical"}
            },
            "holiday_planning": {
                "peak_months": [11, 12],
                "preparation_months": [9, 10],
                "documents_needed": ["gift_lists", "travel_plans", "family_contacts", "recipes"],
                "typical_actions": ["plan_gatherings", "book_travel", "prepare_gifts"],
                "urgency_curve": {9: "low", 10: "medium", 11: "high", 12: "critical"}
            },
            "annual_reviews": {
                "peak_months": [12, 1],  # End of year/beginning of year
                "preparation_months": [11],
                "documents_needed": ["performance_reviews", "goals", "budgets", "contracts"],
                "typical_actions": ["review_goals", "plan_budget", "schedule_reviews"],
                "urgency_curve": {11: "medium", 12: "high", 1: "high"}
            },
            "insurance_renewals": {
                "peak_months": list(range(1, 13)),  # Varies by individual
                "preparation_months": [],  # Calculated per user
                "documents_needed": ["policies", "claims_history", "coverage_comparison"],
                "typical_actions": ["review_coverage", "compare_quotes", "update_beneficiaries"],
                "urgency_curve": {}  # Calculated per policy
            }
        }
    
    def _load_compliance_calendar(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load compliance and deadline calendar."""
        return {
            "tax_deadlines": [
                {"date": "01-31", "description": "W2 forms due from employers", "type": "document_receipt"},
                {"date": "03-15", "description": "Corporate tax returns due", "type": "business_filing"},
                {"date": "04-15", "description": "Individual tax returns due", "type": "personal_filing"},
                {"date": "10-15", "description": "Tax extension deadline", "type": "extension_filing"}
            ],
            "business_compliance": [
                {"date": "03-31", "description": "Q1 reports due", "type": "quarterly_filing"},
                {"date": "06-30", "description": "Q2 reports due", "type": "quarterly_filing"},
                {"date": "09-30", "description": "Q3 reports due", "type": "quarterly_filing"},
                {"date": "12-31", "description": "Q4 reports and annual filings due", "type": "annual_filing"}
            ],
            "personal_finance": [
                {"date": "12-31", "description": "FSA/HSA use-it-or-lose-it deadline", "type": "benefit_deadline"},
                {"date": "04-15", "description": "IRA contribution deadline", "type": "investment_deadline"},
                {"date": "12-15", "description": "Health insurance open enrollment ends", "type": "enrollment_deadline"}
            ]
        }
    
    def _load_life_event_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load patterns that indicate life events."""
        return {
            "job_change": {
                "keywords": ["interview", "resume", "job", "career", "offer", "salary", "benefits"],
                "file_patterns": ["resume", "cover_letter", "job_description"],
                "timeline": "1-3 months",
                "implications": ["update_insurance", "401k_rollover", "address_change", "tax_implications"]
            },
            "moving": {
                "keywords": ["house", "apartment", "moving", "relocation", "address", "lease", "mortgage"],
                "file_patterns": ["lease", "mortgage", "moving_checklist", "address_change"],
                "timeline": "2-6 months",
                "implications": ["address_updates", "utility_transfers", "school_transfers", "voter_registration"]
            },
            "marriage": {
                "keywords": ["wedding", "marriage", "engagement", "spouse", "ceremony", "reception"],
                "file_patterns": ["wedding_plans", "marriage_certificate", "name_change"],
                "timeline": "6-18 months",
                "implications": ["name_change", "tax_status_change", "insurance_updates", "beneficiary_updates"]
            },
            "having_children": {
                "keywords": ["baby", "pregnancy", "maternity", "paternity", "childcare", "pediatrician"],
                "file_patterns": ["baby_preparations", "childcare", "medical_records"],
                "timeline": "9-12 months",
                "implications": ["insurance_updates", "tax_benefits", "childcare_arrangements", "will_updates"]
            },
            "retirement_planning": {
                "keywords": ["retirement", "pension", "401k", "social_security", "medicare", "estate"],
                "file_patterns": ["retirement_plans", "financial_statements", "estate_documents"],
                "timeline": "1-5 years",
                "implications": ["financial_planning", "healthcare_planning", "estate_planning", "tax_planning"]
            },
            "health_issues": {
                "keywords": ["medical", "doctor", "hospital", "surgery", "treatment", "insurance_claim"],
                "file_patterns": ["medical_records", "insurance_claims", "treatment_plans"],
                "timeline": "immediate-ongoing",
                "implications": ["insurance_navigation", "medical_records_organization", "financial_planning"]
            }
        }
    
    def detect_seasonal_needs(self, current_date: datetime, user_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect upcoming seasonal needs."""
        seasonal_needs = []
        current_month = current_date.month
        
        for pattern_name, pattern_info in self.seasonal_patterns.items():
            # Check if we're approaching a peak month
            for peak_month in pattern_info["peak_months"]:
                months_until_peak = (peak_month - current_month) % 12
                
                # Predict 1-4 months ahead
                if 1 <= months_until_peak <= 4:
                    urgency = self._calculate_seasonal_urgency(months_until_peak, pattern_info)
                    certainty = self._calculate_seasonal_certainty(pattern_name, user_history)
                    
                    seasonal_need = {
                        "pattern_name": pattern_name,
                        "predicted_month": peak_month,
                        "months_until": months_until_peak,
                        "urgency": urgency,
                        "certainty": certainty,
                        "documents_needed": pattern_info["documents_needed"],
                        "actions": pattern_info["typical_actions"]
                    }
                    
                    seasonal_needs.append(seasonal_need)
        
        return seasonal_needs
    
    def detect_compliance_deadlines(self, current_date: datetime, user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect upcoming compliance deadlines."""
        upcoming_deadlines = []
        current_year = current_date.year
        
        # Determine which compliance categories apply to user
        applicable_categories = self._determine_applicable_compliance(user_profile)
        
        for category in applicable_categories:
            if category in self.compliance_calendar:
                for deadline_info in self.compliance_calendar[category]:
                    deadline_date = self._parse_deadline_date(deadline_info["date"], current_year)
                    
                    # Look for deadlines 1-90 days ahead
                    days_until = (deadline_date - current_date).days
                    if 1 <= days_until <= 90:
                        urgency = self._calculate_deadline_urgency(days_until)
                        
                        upcoming_deadlines.append({
                            "category": category,
                            "deadline_date": deadline_date,
                            "days_until": days_until,
                            "description": deadline_info["description"],
                            "type": deadline_info["type"],
                            "urgency": urgency,
                            "certainty": "certain"  # Compliance deadlines are certain
                        })
        
        return upcoming_deadlines
    
    def _calculate_seasonal_urgency(self, months_until: int, pattern_info: Dict[str, Any]) -> str:
        """Calculate urgency based on time until seasonal event."""
        urgency_curve = pattern_info.get("urgency_curve", {})
        
        # Default urgency calculation
        if months_until <= 1:
            return "critical"
        elif months_until <= 2:
            return "high"
        elif months_until <= 3:
            return "medium"
        else:
            return "low"
    
    def _calculate_seasonal_certainty(self, pattern_name: str, user_history: List[Dict[str, Any]]) -> str:
        """Calculate certainty based on user's historical patterns."""
        # Check if user has shown this pattern before
        historical_matches = sum(1 for item in user_history 
                               if pattern_name.replace("_", " ") in item.get("content", "").lower())
        
        if historical_matches >= 3:
            return "certain"
        elif historical_matches >= 2:
            return "very_likely"
        elif historical_matches >= 1:
            return "likely"
        else:
            return "possible"
    
    def _determine_applicable_compliance(self, user_profile: Dict[str, Any]) -> List[str]:
        """Determine which compliance categories apply to a user."""
        applicable = ["personal_finance"]  # Everyone has personal finance needs
        
        if user_profile.get("has_business", False):
            applicable.append("business_compliance")
        
        if user_profile.get("files_taxes", True):
            applicable.append("tax_deadlines")
        
        return applicable
    
    def _parse_deadline_date(self, date_str: str, year: int) -> datetime:
        """Parse deadline date string (MM-DD format) into datetime."""
        month, day = map(int, date_str.split("-"))
        return datetime(year, month, day)
    
    def _calculate_deadline_urgency(self, days_until: int) -> str:
        """Calculate urgency based on days until deadline."""
        if days_until <= 7:
            return "critical"
        elif days_until <= 30:
            return "high"
        elif days_until <= 60:
            return "medium"
        else:
            return "low"

class LifeEventDetector:
    """Detects life events from user data patterns."""
    
    def __init__(self):
        self.event_patterns = TemporalPatternDetector()._load_life_event_patterns()
        self.detection_thresholds = {
            "keyword_matches": 3,
            "file_pattern_matches": 2,
            "time_clustering": 0.7
        }
    
    def detect_life_events(self, user_id: str, user_data: List[Dict[str, Any]], 
                          time_window_days: int = 90) -> List[LifeEvent]:
        """Detect potential life events from user data."""
        detected_events = []
        cutoff_date = datetime.now() - timedelta(days=time_window_days)
        
        # Filter recent data
        recent_data = [
            item for item in user_data
            if item.get("timestamp", datetime.now()) > cutoff_date
        ]
        
        for event_type, pattern_info in self.event_patterns.items():
            event = self._detect_specific_event(user_id, event_type, pattern_info, recent_data)
            if event:
                detected_events.append(event)
        
        return detected_events
    
    def _detect_specific_event(self, user_id: str, event_type: str, 
                             pattern_info: Dict[str, Any], 
                             recent_data: List[Dict[str, Any]]) -> Optional[LifeEvent]:
        """Detect a specific type of life event."""
        
        # Count keyword matches
        all_text = " ".join([
            f"{item.get('filename', '')} {item.get('content', '')}"
            for item in recent_data
        ]).lower()
        
        keyword_matches = sum(1 for keyword in pattern_info["keywords"] if keyword in all_text)
        
        # Count file pattern matches
        file_pattern_matches = 0
        for item in recent_data:
            filename = item.get("filename", "").lower()
            for pattern in pattern_info["file_patterns"]:
                if pattern in filename:
                    file_pattern_matches += 1
                    break
        
        # Calculate confidence
        confidence = self._calculate_event_confidence(keyword_matches, file_pattern_matches, pattern_info)
        
        if confidence >= 0.6:  # 60% confidence threshold
            # Predict when this event might occur
            predicted_date = self._predict_event_timeline(pattern_info["timeline"])
            
            event = LifeEvent(
                event_id=f"event_{user_id}_{event_type}_{datetime.now().timestamp()}",
                user_id=user_id,
                event_type=event_type,
                event_name=event_type.replace("_", " ").title(),
                predicted_date=predicted_date,
                confidence=confidence,
                triggers=[f"{keyword_matches} keyword matches", f"{file_pattern_matches} file patterns"],
                implications=pattern_info["implications"]
            )
            
            return event
        
        return None
    
    def _calculate_event_confidence(self, keyword_matches: int, file_pattern_matches: int, 
                                  pattern_info: Dict[str, Any]) -> float:
        """Calculate confidence score for life event detection."""
        # Base confidence from keyword matches
        keyword_confidence = min(keyword_matches / len(pattern_info["keywords"]), 1.0)
        
        # File pattern confidence
        pattern_confidence = min(file_pattern_matches / len(pattern_info["file_patterns"]), 1.0)
        
        # Weighted average
        confidence = (keyword_confidence * 0.6) + (pattern_confidence * 0.4)
        
        return confidence
    
    def _predict_event_timeline(self, timeline_str: str) -> datetime:
        """Predict when an event will occur based on timeline string."""
        current_date = datetime.now()
        
        if "immediate" in timeline_str:
            return current_date + timedelta(days=7)
        elif "1-3 months" in timeline_str:
            return current_date + timedelta(days=60)  # 2 months
        elif "2-6 months" in timeline_str:
            return current_date + timedelta(days=120)  # 4 months
        elif "6-18 months" in timeline_str:
            return current_date + timedelta(days=365)  # 1 year
        elif "1-5 years" in timeline_str:
            return current_date + timedelta(days=730)  # 2 years
        else:
            return current_date + timedelta(days=90)  # Default 3 months

class PredictiveAnalyzer:
    """Advanced predictive analysis for future needs."""
    
    def __init__(self):
        self.prediction_models = {
            "seasonal": 0.8,      # Seasonal patterns are highly predictable
            "compliance": 0.95,   # Compliance deadlines are certain
            "life_events": 0.6,   # Life events are less predictable
            "behavioral": 0.7     # Behavioral patterns are moderately predictable
        }
    
    def analyze_future_document_needs(self, user_id: str, current_documents: List[Dict[str, Any]], 
                                    upcoming_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze what documents user will likely need in the future."""
        predicted_needs = []
        
        # Document needs based on upcoming events
        for event in upcoming_events:
            event_type = event.get("type", "")
            
            # Tax season document needs
            if "tax" in event_type.lower():
                needed_docs = self._predict_tax_documents(user_id, current_documents)
                predicted_needs.extend(needed_docs)
            
            # Travel document needs
            elif "travel" in event_type.lower() or "vacation" in event_type.lower():
                needed_docs = self._predict_travel_documents(user_id, current_documents)
                predicted_needs.extend(needed_docs)
            
            # Business document needs
            elif "business" in event_type.lower() or "work" in event_type.lower():
                needed_docs = self._predict_business_documents(user_id, current_documents)
                predicted_needs.extend(needed_docs)
        
        # Analyze document gaps
        gap_analysis = self._analyze_document_gaps(current_documents)
        predicted_needs.extend(gap_analysis)
        
        return predicted_needs
    
    def _predict_tax_documents(self, user_id: str, current_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Predict what tax documents user will need."""
        needs = []
        current_year = datetime.now().year
        
        # Check for missing common tax documents
        doc_types_present = set()
        for doc in current_docs:
            filename = doc.get("filename", "").lower()
            if "w2" in filename or "w-2" in filename:
                doc_types_present.add("w2")
            elif "1099" in filename:
                doc_types_present.add("1099")
            elif "receipt" in filename:
                doc_types_present.add("receipts")
        
        # Predict needed documents
        if "w2" not in doc_types_present:
            needs.append({
                "document_type": "W2 Forms",
                "urgency": "high",
                "predicted_date": datetime(current_year, 2, 28),
                "reason": "W2 forms are typically needed for tax filing"
            })
        
        if "receipts" not in doc_types_present:
            needs.append({
                "document_type": "Tax Receipts",
                "urgency": "medium",
                "predicted_date": datetime(current_year, 3, 15),
                "reason": "Receipts needed for tax deductions"
            })
        
        return needs
    
    def _predict_travel_documents(self, user_id: str, current_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Predict what travel documents user will need."""
        needs = []
        
        # Check for passport, travel insurance, etc.
        has_passport = any("passport" in doc.get("filename", "").lower() for doc in current_docs)
        has_travel_insurance = any("travel" in doc.get("filename", "").lower() and 
                                 "insurance" in doc.get("filename", "").lower() for doc in current_docs)
        
        if not has_passport:
            needs.append({
                "document_type": "Passport",
                "urgency": "high",
                "predicted_date": datetime.now() + timedelta(days=30),
                "reason": "Passport required for international travel"
            })
        
        if not has_travel_insurance:
            needs.append({
                "document_type": "Travel Insurance",
                "urgency": "medium",
                "predicted_date": datetime.now() + timedelta(days=14),
                "reason": "Travel insurance recommended for trip protection"
            })
        
        return needs
    
    def _predict_business_documents(self, user_id: str, current_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Predict what business documents user will need."""
        needs = []
        
        # Check for common business documents
        has_contracts = any("contract" in doc.get("filename", "").lower() for doc in current_docs)
        has_invoices = any("invoice" in doc.get("filename", "").lower() for doc in current_docs)
        
        current_quarter = (datetime.now().month - 1) // 3 + 1
        next_quarter_start = datetime(datetime.now().year, (current_quarter * 3) + 1, 1)
        
        if has_invoices:
            needs.append({
                "document_type": "Quarterly Business Report",
                "urgency": "medium",
                "predicted_date": next_quarter_start - timedelta(days=15),
                "reason": "Quarterly reports typically due at end of quarter"
            })
        
        return needs
    
    def _analyze_document_gaps(self, current_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze gaps in user's document collection."""
        gaps = []
        
        # Common document types everyone should have
        essential_docs = {
            "identification": ["id", "license", "passport"],
            "financial": ["bank_statement", "tax_return", "insurance"],
            "legal": ["will", "power_of_attorney", "contract"],
            "medical": ["insurance_card", "medical_records", "prescription"]
        }
        
        for category, doc_types in essential_docs.items():
            missing_docs = []
            for doc_type in doc_types:
                has_doc = any(doc_type in doc.get("filename", "").lower() for doc in current_docs)
                if not has_doc:
                    missing_docs.append(doc_type)
            
            if len(missing_docs) >= len(doc_types) // 2:  # Missing more than half
                gaps.append({
                    "category": category,
                    "missing_documents": missing_docs,
                    "urgency": "low",
                    "predicted_date": datetime.now() + timedelta(days=60),
                    "reason": f"Important to have {category} documents organized"
                })
        
        return gaps

class FutureNeedsPredictor:
    """Main future needs prediction engine orchestrator."""
    
    def __init__(self):
        self.temporal_detector = TemporalPatternDetector()
        self.life_event_detector = LifeEventDetector()
        self.predictive_analyzer = PredictiveAnalyzer()
        self.user_predictions = defaultdict(list)
        
        print("🔮 Future Needs Predictor initialized")
    
    async def predict_future_needs(self, user_id: str, user_data: Dict[str, Any],
                                 prediction_horizon_days: int = 120) -> List[FutureNeed]:
        """Predict future needs for a user."""
        current_date = datetime.now()
        predictions = []
        
        # Extract relevant data
        user_history = user_data.get("history", [])
        current_documents = user_data.get("documents", [])
        user_profile = user_data.get("profile", {})
        
        # 1. Detect seasonal needs
        seasonal_needs = self.temporal_detector.detect_seasonal_needs(current_date, user_history)
        for need in seasonal_needs:
            prediction = self._create_seasonal_prediction(user_id, need, current_date)
            if prediction:
                predictions.append(prediction)
        
        # 2. Detect compliance deadlines
        compliance_needs = self.temporal_detector.detect_compliance_deadlines(current_date, user_profile)
        for need in compliance_needs:
            prediction = self._create_compliance_prediction(user_id, need)
            if prediction:
                predictions.append(prediction)
        
        # 3. Detect life events
        life_events = self.life_event_detector.detect_life_events(user_id, user_history)
        for event in life_events:
            prediction = self._create_life_event_prediction(user_id, event)
            if prediction:
                predictions.append(prediction)
        
        # 4. Predict document needs
        document_needs = self.predictive_analyzer.analyze_future_document_needs(
            user_id, current_documents, seasonal_needs + compliance_needs
        )
        for need in document_needs:
            prediction = self._create_document_prediction(user_id, need)
            if prediction:
                predictions.append(prediction)
        
        # Filter by prediction horizon
        horizon_cutoff = current_date + timedelta(days=prediction_horizon_days)
        predictions = [p for p in predictions if p.predicted_date <= horizon_cutoff]
        
        # Sort by predicted date and urgency
        predictions.sort(key=lambda p: (p.predicted_date, p.urgency.value))
        
        # Cache predictions
        self.user_predictions[user_id] = predictions
        
        return predictions
    
    def _create_seasonal_prediction(self, user_id: str, need: Dict[str, Any], 
                                  current_date: datetime) -> Optional[FutureNeed]:
        """Create prediction from seasonal need."""
        pattern_name = need["pattern_name"]
        predicted_month = need["predicted_month"]
        predicted_year = current_date.year
        
        # Adjust year if month has passed
        if predicted_month < current_date.month:
            predicted_year += 1
        
        predicted_date = datetime(predicted_year, predicted_month, 15)  # Mid-month
        
        # Convert string values to enums
        urgency = Urgency(need["urgency"].lower())
        certainty = Certainty(need["certainty"].lower())
        
        prediction_id = f"seasonal_{user_id}_{pattern_name}_{predicted_year}"
        
        return FutureNeed(
            prediction_id=prediction_id,
            user_id=user_id,
            need_type=PredictionType.SEASONAL_NEED,
            title=f"{pattern_name.replace('_', ' ').title()} Preparation",
            description=f"You'll likely need to prepare for {pattern_name.replace('_', ' ')} in {calendar.month_name[predicted_month]}",
            predicted_date=predicted_date,
            urgency=urgency,
            certainty=certainty,
            context={"pattern": pattern_name, "season": calendar.month_name[predicted_month]},
            recommended_actions=need.get("actions", []),
            related_files=need.get("documents_needed", []),
            created_at=datetime.now(),
            expires_at=predicted_date + timedelta(days=30)
        )
    
    def _create_compliance_prediction(self, user_id: str, need: Dict[str, Any]) -> Optional[FutureNeed]:
        """Create prediction from compliance deadline."""
        deadline_date = need["deadline_date"]
        urgency = Urgency(need["urgency"].lower())
        
        prediction_id = f"compliance_{user_id}_{need['type']}_{deadline_date.strftime('%Y%m%d')}"
        
        return FutureNeed(
            prediction_id=prediction_id,
            user_id=user_id,
            need_type=PredictionType.COMPLIANCE_NEED,
            title=f"Upcoming Deadline: {need['description']}",
            description=f"You have a {need['type']} deadline on {deadline_date.strftime('%B %d, %Y')}",
            predicted_date=deadline_date - timedelta(days=7),  # Remind 1 week early
            urgency=urgency,
            certainty=Certainty.CERTAIN,
            context={"category": need["category"], "deadline": deadline_date.isoformat()},
            recommended_actions=[f"Prepare for {need['description'].lower()}", "Gather required documents"],
            related_files=[],
            created_at=datetime.now(),
            expires_at=deadline_date
        )
    
    def _create_life_event_prediction(self, user_id: str, event: LifeEvent) -> Optional[FutureNeed]:
        """Create prediction from life event."""
        prediction_id = f"life_event_{event.event_id}"
        
        # Determine urgency based on confidence and timeline
        if event.confidence >= 0.8:
            urgency = Urgency.HIGH
        elif event.confidence >= 0.6:
            urgency = Urgency.MEDIUM
        else:
            urgency = Urgency.LOW
        
        # Convert confidence to certainty
        if event.confidence >= 0.9:
            certainty = Certainty.CERTAIN
        elif event.confidence >= 0.75:
            certainty = Certainty.VERY_LIKELY
        elif event.confidence >= 0.5:
            certainty = Certainty.LIKELY
        else:
            certainty = Certainty.POSSIBLE
        
        return FutureNeed(
            prediction_id=prediction_id,
            user_id=user_id,
            need_type=PredictionType.LIFE_EVENT,
            title=f"Potential Life Event: {event.event_name}",
            description=f"You may be planning for {event.event_name.lower()} based on recent activity",
            predicted_date=event.predicted_date,
            urgency=urgency,
            certainty=certainty,
            context={"event_type": event.event_type, "confidence": event.confidence},
            recommended_actions=[f"Plan for {implication}" for implication in event.implications[:3]],
            related_files=event.triggers,
            created_at=datetime.now(),
            expires_at=event.predicted_date + timedelta(days=30)
        )
    
    def _create_document_prediction(self, user_id: str, need: Dict[str, Any]) -> Optional[FutureNeed]:
        """Create prediction from document need."""
        prediction_id = f"document_{user_id}_{need['document_type'].replace(' ', '_').lower()}"
        
        urgency = Urgency(need["urgency"].lower())
        predicted_date = need["predicted_date"]
        
        return FutureNeed(
            prediction_id=prediction_id,
            user_id=user_id,
            need_type=PredictionType.DOCUMENT_NEED,
            title=f"Document Needed: {need['document_type']}",
            description=need["reason"],
            predicted_date=predicted_date,
            urgency=urgency,
            certainty=Certainty.LIKELY,
            context={"document_type": need["document_type"]},
            recommended_actions=[f"Locate or obtain {need['document_type']}", "Scan and organize document"],
            related_files=[need["document_type"]],
            created_at=datetime.now(),
            expires_at=predicted_date + timedelta(days=14)
        )
    
    async def get_user_predictions(self, user_id: str) -> List[FutureNeed]:
        """Get cached predictions for a user."""
        return self.user_predictions.get(user_id, [])
    
    async def get_urgent_predictions(self, user_id: str, days_ahead: int = 30) -> List[FutureNeed]:
        """Get urgent predictions within specified days."""
        all_predictions = await self.get_user_predictions(user_id)
        cutoff_date = datetime.now() + timedelta(days=days_ahead)
        
        urgent = [
            p for p in all_predictions
            if p.predicted_date <= cutoff_date and p.urgency in [Urgency.HIGH, Urgency.CRITICAL]
        ]
        
        return urgent
    
    async def acknowledge_prediction(self, user_id: str, prediction_id: str) -> Dict[str, Any]:
        """Mark a prediction as acknowledged by the user."""
        user_predictions = self.user_predictions.get(user_id, [])
        
        for prediction in user_predictions:
            if prediction.prediction_id == prediction_id:
                # In a real implementation, this would update database
                print(f"✅ User {user_id} acknowledged prediction: {prediction.title}")
                return {
                    "success": True,
                    "prediction_id": prediction_id,
                    "acknowledged_at": datetime.now().isoformat()
                }
        
        return {"success": False, "error": "Prediction not found"}
    
    async def get_prediction_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get analytics about predictions for a user."""
        predictions = await self.get_user_predictions(user_id)
        
        if not predictions:
            return {"message": "No predictions available"}
        
        # Analyze predictions
        by_type = defaultdict(int)
        by_urgency = defaultdict(int)
        by_certainty = defaultdict(int)
        
        for pred in predictions:
            by_type[pred.need_type.value] += 1
            by_urgency[pred.urgency.value] += 1
            by_certainty[pred.certainty.value] += 1
        
        # Upcoming predictions (next 30 days)
        upcoming = [p for p in predictions if (p.predicted_date - datetime.now()).days <= 30]
        
        return {
            "total_predictions": len(predictions),
            "upcoming_30_days": len(upcoming),
            "by_type": dict(by_type),
            "by_urgency": dict(by_urgency),
            "by_certainty": dict(by_certainty),
            "next_prediction": min(predictions, key=lambda p: p.predicted_date).title if predictions else None,
            "prediction_horizon_days": max((p.predicted_date - datetime.now()).days for p in predictions) if predictions else 0
        }

# CLI interface for testing
async def main():
    """CLI interface for Future Needs Predictor testing."""
    predictor = FutureNeedsPredictor()
    
    print("🔮 Future Needs Predictor Test Suite")
    print("=" * 50)
    
    # Test 1: Create mock user data
    print("\n1. Creating mock user data...")
    
    user_id = "test_user"
    current_date = datetime.now()
    
    mock_user_data = {
        "profile": {
            "has_business": True,
            "files_taxes": True,
            "age_group": "working_adult",
            "family_status": "married"
        },
        "history": [
            {"content": "tax preparation software downloaded", "timestamp": current_date - timedelta(days=20)},
            {"content": "receipt for business expense", "timestamp": current_date - timedelta(days=15)},
            {"content": "vacation planning hawaii flights", "timestamp": current_date - timedelta(days=30)},
            {"content": "wedding planning venue booking", "timestamp": current_date - timedelta(days=45)},
            {"content": "job interview preparation resume", "timestamp": current_date - timedelta(days=10)}
        ],
        "documents": [
            {"filename": "receipt_2024_01.jpg", "type": "financial"},
            {"filename": "vacation_itinerary.pdf", "type": "travel"},
            {"filename": "business_contract.docx", "type": "business"},
            {"filename": "wedding_checklist.xlsx", "type": "personal"}
        ]
    }
    
    print(f"✅ Created mock user data with {len(mock_user_data['documents'])} documents")
    
    # Test 2: Predict future needs
    print("\n2. Predicting future needs...")
    
    predictions = await predictor.predict_future_needs(user_id, mock_user_data, 120)
    
    print(f"✅ Generated {len(predictions)} predictions:")
    for i, prediction in enumerate(predictions[:5], 1):
        print(f"   {i}. {prediction.title}")
        print(f"      Date: {prediction.predicted_date.strftime('%B %d, %Y')}")
        print(f"      Urgency: {prediction.urgency.value}, Certainty: {prediction.certainty.value}")
        print(f"      Type: {prediction.need_type.value}")
        print(f"      Description: {prediction.description}")
    
    # Test 3: Get urgent predictions
    print("\n3. Getting urgent predictions...")
    
    urgent_predictions = await predictor.get_urgent_predictions(user_id, 30)
    
    print(f"✅ Found {len(urgent_predictions)} urgent predictions in next 30 days:")
    for prediction in urgent_predictions:
        days_until = (prediction.predicted_date - datetime.now()).days
        print(f"   - {prediction.title} ({days_until} days away)")
    
    # Test 4: Test seasonal detection
    print("\n4. Testing seasonal pattern detection...")
    
    # Simulate it's February (tax season approach)
    february_date = datetime(2024, 2, 15)
    seasonal_needs = predictor.temporal_detector.detect_seasonal_needs(
        february_date, mock_user_data["history"]
    )
    
    print(f"✅ Detected {len(seasonal_needs)} seasonal patterns for February:")
    for need in seasonal_needs[:3]:
        print(f"   - {need['pattern_name']}: {need['months_until']} months until peak")
        print(f"     Urgency: {need['urgency']}, Certainty: {need['certainty']}")
    
    # Test 5: Test life event detection
    print("\n5. Testing life event detection...")
    
    life_events = predictor.life_event_detector.detect_life_events(
        user_id, mock_user_data["history"]
    )
    
    print(f"✅ Detected {len(life_events)} potential life events:")
    for event in life_events:
        print(f"   - {event.event_name}: {event.confidence:.1%} confidence")
        print(f"     Predicted date: {event.predicted_date.strftime('%B %Y')}")
        print(f"     Implications: {', '.join(event.implications[:3])}")
    
    # Test 6: Acknowledge prediction
    print("\n6. Testing prediction acknowledgment...")
    
    if predictions:
        prediction_to_ack = predictions[0]
        result = await predictor.acknowledge_prediction(user_id, prediction_to_ack.prediction_id)
        
        if result["success"]:
            print(f"✅ Acknowledged prediction: {prediction_to_ack.title}")
        else:
            print(f"❌ Failed to acknowledge: {result['error']}")
    
    # Test 7: Get analytics
    print("\n7. Getting prediction analytics...")
    
    analytics = await predictor.get_prediction_analytics(user_id)
    
    if "message" not in analytics:
        print(f"✅ Prediction analytics:")
        print(f"   Total predictions: {analytics['total_predictions']}")
        print(f"   Upcoming (30 days): {analytics['upcoming_30_days']}")
        print(f"   By type: {analytics['by_type']}")
        print(f"   By urgency: {analytics['by_urgency']}")
        print(f"   Next prediction: {analytics['next_prediction']}")
        print(f"   Horizon: {analytics['prediction_horizon_days']} days")
    else:
        print(f"ℹ️ {analytics['message']}")
    
    print("\n🎉 Future Needs Predictor tests completed!")

if __name__ == "__main__":
    asyncio.run(main())