"""
Educational Platform with Guides and AI Tools
Comprehensive learning resources for both app owners and investors
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import sqlite3
import json
from datetime import datetime
import uuid
import random

router = APIRouter(prefix="/education", tags=["Education"])

DATABASE_PATH = "fundraising_platform.db"

def get_db_connection():
    return sqlite3.connect(DATABASE_PATH)

# Pydantic models
class PitchPractice(BaseModel):
    app_name: str
    industry: str
    pitch_content: str
    target_funding: float

class ValuationInputs(BaseModel):
    annual_revenue: float
    growth_rate: float
    market_size: float
    competition_level: str
    team_experience: str
    traction: str

class TermSheetInputs(BaseModel):
    company_name: str
    investment_amount: float
    pre_money_valuation: float
    investor_rights: List[str]
    board_composition: Dict[str, int]
    liquidation_preference: str

@router.get("/pitch-guide")
async def pitch_guide():
    """Complete guide on how to pitch your app to investors"""
    guide_content = {
        "title": "The Complete App Pitching Guide",
        "sections": [
            {
                "title": "1. Executive Summary",
                "content": "Start with a compelling hook that explains what your app does in one sentence.",
                "tips": [
                    "Keep it under 30 seconds to explain",
                    "Focus on the problem you solve",
                    "Mention your unique solution",
                    "Include impressive metrics if available"
                ],
                "examples": [
                    "We're building the Uber for grocery delivery in rural areas",
                    "Our app increases workplace productivity by 40% through AI-powered task management"
                ]
            },
            {
                "title": "2. Problem Statement",
                "content": "Clearly define the problem your app solves and why it matters.",
                "tips": [
                    "Use real data and statistics",
                    "Make it relatable to investors",
                    "Show the size of the problem",
                    "Explain why existing solutions fail"
                ],
                "common_mistakes": [
                    "Making the problem too broad",
                    "Not quantifying the problem size",
                    "Assuming everyone understands the problem"
                ]
            },
            {
                "title": "3. Solution & Product Demo",
                "content": "Present your app and show how it solves the identified problem.",
                "tips": [
                    "Show, don't just tell",
                    "Use actual app screenshots or demo",
                    "Highlight key features that differentiate you",
                    "Keep the demo under 2 minutes"
                ]
            },
            {
                "title": "4. Market Opportunity",
                "content": "Define your target market and the opportunity size.",
                "key_metrics": [
                    "Total Addressable Market (TAM)",
                    "Serviceable Available Market (SAM)",
                    "Serviceable Obtainable Market (SOM)",
                    "Market growth rate"
                ]
            },
            {
                "title": "5. Business Model",
                "content": "Explain how you make money and your revenue streams.",
                "revenue_models": [
                    "Subscription (SaaS)",
                    "Freemium",
                    "In-app purchases",
                    "Advertising",
                    "Commission/Transaction fees",
                    "One-time purchase"
                ]
            },
            {
                "title": "6. Traction & Metrics",
                "content": "Show evidence that your app is gaining momentum.",
                "key_metrics": [
                    "Monthly Active Users (MAU)",
                    "Daily Active Users (DAU)",
                    "Monthly Recurring Revenue (MRR)",
                    "Customer Acquisition Cost (CAC)",
                    "Lifetime Value (LTV)",
                    "Retention rates"
                ]
            },
            {
                "title": "7. Competition Analysis",
                "content": "Acknowledge competitors and explain your competitive advantage.",
                "framework": "Use a competitive matrix showing features comparison"
            },
            {
                "title": "8. Team",
                "content": "Introduce your team and why you're the right people to build this.",
                "include": [
                    "Relevant experience",
                    "Technical skills",
                    "Industry expertise",
                    "Previous successes"
                ]
            },
            {
                "title": "9. Financial Projections",
                "content": "Present realistic financial forecasts for 3-5 years.",
                "include": [
                    "Revenue projections",
                    "User growth projections",
                    "Key assumptions",
                    "Unit economics"
                ]
            },
            {
                "title": "10. Funding Ask",
                "content": "Clearly state how much you're raising and what you'll use it for.",
                "structure": {
                    "amount": "Specific dollar amount",
                    "timeline": "How long this funding will last",
                    "use_of_funds": "Detailed breakdown of spending",
                    "milestones": "What you'll achieve with this funding"
                }
            }
        ],
        "pitch_deck_template": {
            "slides": [
                "Title Slide",
                "Problem",
                "Solution",
                "Market Size",
                "Product Demo",
                "Business Model",
                "Traction",
                "Competition",
                "Team",
                "Financials",
                "Funding Ask",
                "Thank You & Contact"
            ],
            "total_slides": "10-12 slides for pitch, detailed appendix for Q&A"
        },
        "presentation_tips": [
            "Practice your pitch until you can do it naturally",
            "Prepare for common investor questions",
            "Have a backup plan if technology fails",
            "Time your presentation (aim for 10-15 minutes)",
            "Tell a story, don't just present data",
            "Show passion and enthusiasm",
            "Be honest about challenges and risks"
        ],
        "common_questions": [
            "How do you plan to acquire customers?",
            "What's your defensibility/moat?",
            "How big can this business become?",
            "What are the biggest risks?",
            "How will you use the funding?",
            "What's your exit strategy?",
            "How do you handle competition?"
        ]
    }
    
    return guide_content

@router.post("/ai-pitch-practice")
async def ai_pitch_practice(pitch_practice: PitchPractice):
    """AI-powered pitch practice with feedback"""
    
    # Simulate AI analysis of the pitch
    feedback = analyze_pitch_with_ai(pitch_practice)
    
    # Store practice session
    conn = get_db_connection()
    cursor = conn.cursor()
    
    practice_id = str(uuid.uuid4())
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pitch_practice_sessions (
            id TEXT PRIMARY KEY,
            app_name TEXT,
            industry TEXT,
            pitch_content TEXT,
            target_funding REAL,
            feedback TEXT,
            score REAL,
            created_at TEXT
        )
    ''')
    
    cursor.execute('''
        INSERT INTO pitch_practice_sessions (
            id, app_name, industry, pitch_content, target_funding,
            feedback, score, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        practice_id, pitch_practice.app_name, pitch_practice.industry,
        pitch_practice.pitch_content, pitch_practice.target_funding,
        json.dumps(feedback), feedback['overall_score'], datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "practice_id": practice_id,
        "feedback": feedback,
        "next_steps": generate_improvement_plan(feedback)
    }

@router.post("/valuation-calculator")
async def valuation_calculator(inputs: ValuationInputs):
    """AI-powered valuation calculator for apps"""
    
    # Calculate valuation using multiple methods
    valuations = calculate_app_valuation(inputs)
    
    return {
        "valuations": valuations,
        "recommended_range": {
            "low": min(valuations.values()),
            "high": max(valuations.values()),
            "suggested": sum(valuations.values()) / len(valuations)
        },
        "methodology_explanation": {
            "revenue_multiple": "Based on industry-standard revenue multiples for your sector",
            "dcf_model": "Discounted cash flow based on projected growth",
            "comparable_analysis": "Comparison with similar apps and their valuations",
            "market_based": "Market size and penetration potential analysis"
        },
        "factors_analysis": analyze_valuation_factors(inputs),
        "recommendations": generate_valuation_recommendations(inputs, valuations)
    }

@router.post("/term-sheet-generator")
async def term_sheet_generator(inputs: TermSheetInputs):
    """Generate a professional term sheet template"""
    
    # Calculate key terms
    post_money_valuation = inputs.pre_money_valuation + inputs.investment_amount
    equity_percentage = (inputs.investment_amount / post_money_valuation) * 100
    
    term_sheet = {
        "company_info": {
            "company_name": inputs.company_name,
            "investment_date": datetime.now().strftime("%B %d, %Y")
        },
        "investment_terms": {
            "investment_amount": f"${inputs.investment_amount:,.2f}",
            "pre_money_valuation": f"${inputs.pre_money_valuation:,.2f}",
            "post_money_valuation": f"${post_money_valuation:,.2f}",
            "equity_percentage": f"{equity_percentage:.2f}%",
            "price_per_share": f"${inputs.pre_money_valuation / 1000000:.2f}"  # Assuming 1M shares
        },
        "investor_rights": inputs.investor_rights,
        "governance": {
            "board_composition": inputs.board_composition,
            "voting_rights": "Proportional to equity ownership",
            "information_rights": "Monthly financial statements, annual budget"
        },
        "economic_terms": {
            "liquidation_preference": inputs.liquidation_preference,
            "dividend_rights": "Non-cumulative dividends when declared",
            "anti_dilution": "Weighted average broad-based",
            "pay_to_play": "Standard pay-to-play provision"
        },
        "other_provisions": {
            "drag_along": "Standard drag-along rights",
            "tag_along": "Standard tag-along rights",
            "right_of_first_refusal": "Company has ROFR on share transfers",
            "co_sale_rights": "Investors have co-sale rights"
        },
        "conditions_precedent": [
            "Completion of due diligence",
            "Execution of definitive agreements",
            "Board approval of transaction",
            "No material adverse changes"
        ],
        "template_sections": generate_detailed_term_sheet_sections(inputs),
        "legal_disclaimers": [
            "This term sheet is for discussion purposes only",
            "Not legally binding until definitive agreements executed",
            "Subject to completion of due diligence",
            "Consult legal counsel before proceeding"
        ]
    }
    
    return term_sheet

@router.get("/success-stories")
async def success_stories():
    """Curated success stories and case studies"""
    
    stories = [
        {
            "app_name": "TaskFlow Pro",
            "category": "Productivity",
            "funding_raised": 250000,
            "valuation": 2500000,
            "investors": 45,
            "story": {
                "problem": "Remote teams struggled with task coordination and productivity tracking",
                "solution": "AI-powered task management with real-time collaboration features",
                "key_metrics": {
                    "users": "50K+ active users",
                    "revenue": "$25K MRR",
                    "growth": "15% month-over-month",
                    "retention": "85% monthly retention"
                },
                "success_factors": [
                    "Strong product-market fit validation",
                    "Experienced team with domain expertise",
                    "Clear monetization strategy",
                    "Impressive user growth metrics"
                ],
                "timeline": "6 months from concept to funding",
                "outcome": "Successfully raised Series A after 12 months"
            },
            "lessons_learned": [
                "Focus on one core problem first",
                "Get paying customers before raising",
                "Build relationships with investors early",
                "Demonstrate clear unit economics"
            ]
        },
        {
            "app_name": "HealthTracker+",
            "category": "Health & Fitness",
            "funding_raised": 500000,
            "valuation": 4000000,
            "investors": 78,
            "story": {
                "problem": "People needed better ways to track health metrics and get personalized insights",
                "solution": "Comprehensive health tracking with AI-powered recommendations",
                "key_metrics": {
                    "users": "100K+ downloads",
                    "revenue": "$40K MRR",
                    "growth": "20% month-over-month",
                    "retention": "75% monthly retention"
                },
                "success_factors": [
                    "Leveraged health data trends",
                    "Strong user engagement metrics",
                    "Partnerships with healthcare providers",
                    "Regulatory compliance from day one"
                ],
                "timeline": "8 months from MVP to funding",
                "outcome": "Acquired by major health company after 18 months"
            },
            "lessons_learned": [
                "Compliance is crucial in health tech",
                "User data privacy builds trust",
                "Healthcare partnerships accelerate growth",
                "Focus on engagement over downloads"
            ]
        },
        {
            "app_name": "LocalMarket",
            "category": "E-commerce",
            "funding_raised": 750000,
            "valuation": 6000000,
            "investors": 120,
            "story": {
                "problem": "Small local businesses lacked online presence and delivery capabilities",
                "solution": "Hyperlocal marketplace connecting businesses with nearby customers",
                "key_metrics": {
                    "merchants": "500+ active merchants",
                    "revenue": "$60K MRR",
                    "growth": "25% month-over-month",
                    "orders": "10K+ monthly orders"
                },
                "success_factors": [
                    "Two-sided marketplace network effects",
                    "Strong local community engagement",
                    "Efficient logistics and delivery",
                    "Data-driven merchant tools"
                ],
                "timeline": "12 months from launch to funding",
                "outcome": "Expanding to 5 new cities with Series B funding"
            },
            "lessons_learned": [
                "Start local and expand gradually",
                "Build supply side first",
                "Community engagement drives growth",
                "Operations are key to marketplace success"
            ]
        }
    ]
    
    return {
        "success_stories": stories,
        "key_patterns": [
            "Strong product-market fit before raising",
            "Focus on metrics that matter to investors",
            "Build relationships before you need them",
            "Demonstrate clear path to profitability",
            "Have experienced team or advisors",
            "Show traction through user engagement"
        ],
        "common_traits": {
            "timing": "Average 6-12 months from MVP to funding",
            "metrics": "Strong user retention and growth metrics",
            "team": "Domain expertise and technical skills",
            "market": "Clear target market and go-to-market strategy"
        }
    }

@router.get("/investor-matching")
async def investor_matching(app_category: str, funding_stage: str, funding_amount: float):
    """AI-powered investor matching service"""
    
    # Simulate investor database and matching
    matches = find_matching_investors(app_category, funding_stage, funding_amount)
    
    return {
        "matched_investors": matches,
        "matching_score_explanation": {
            "category_fit": "Investor's focus areas match your app category",
            "stage_fit": "Investor typically invests at your funding stage",
            "check_size": "Investment amount fits investor's typical check size",
            "geography": "Investor location and preferences",
            "network": "Mutual connections and warm introductions available"
        },
        "outreach_recommendations": generate_outreach_recommendations(matches),
        "introduction_templates": generate_introduction_templates()
    }

@router.get("/mentorship-program")
async def mentorship_program():
    """Information about the mentorship program"""
    
    return {
        "program_overview": {
            "description": "Connect with experienced entrepreneurs and investors",
            "duration": "3-6 months",
            "format": "1-on-1 monthly sessions + group workshops",
            "cost": "Free for active fundraising campaigns"
        },
        "mentor_categories": [
            {
                "category": "Technical Founders",
                "expertise": ["Product development", "Technical architecture", "Engineering team building"],
                "available_mentors": 15
            },
            {
                "category": "Business Development",
                "expertise": ["Go-to-market strategy", "Sales", "Partnerships", "Business model"],
                "available_mentors": 12
            },
            {
                "category": "Fundraising Experts",
                "expertise": ["Investor relations", "Pitch development", "Term negotiations"],
                "available_mentors": 8
            },
            {
                "category": "Industry Specialists",
                "expertise": ["Healthcare", "FinTech", "E-commerce", "SaaS"],
                "available_mentors": 20
            }
        ],
        "application_process": [
            "Submit app listing on platform",
            "Complete mentor matching questionnaire",
            "Review mentor profiles and preferences",
            "Schedule initial meeting",
            "Begin mentorship program"
        ],
        "success_metrics": {
            "mentor_satisfaction": "4.8/5 average rating",
            "fundraising_success_rate": "65% of mentees successfully raise funding",
            "program_completion_rate": "85%"
        }
    }

@router.get("/legal-templates")
async def legal_templates():
    """Legal document templates and resources"""
    
    return {
        "available_templates": [
            {
                "name": "Non-Disclosure Agreement (NDA)",
                "description": "Protect confidential information during investor discussions",
                "format": "PDF, Word",
                "customization_required": ["Company name", "Parties", "Specific terms"]
            },
            {
                "name": "Convertible Note Agreement",
                "description": "Standard convertible note for early-stage funding",
                "format": "PDF, Word",
                "customization_required": ["Investment amount", "Valuation cap", "Discount rate", "Maturity date"]
            },
            {
                "name": "SAFE Agreement",
                "description": "Simple Agreement for Future Equity (Y Combinator standard)",
                "format": "PDF, Word",
                "customization_required": ["Investment amount", "Valuation cap", "Discount rate"]
            },
            {
                "name": "Subscription Agreement",
                "description": "For equity investments and share purchases",
                "format": "PDF, Word",
                "customization_required": ["Share details", "Investment terms", "Investor information"]
            },
            {
                "name": "Shareholder Agreement",
                "description": "Govern relationship between company and investors",
                "format": "PDF, Word",
                "customization_required": ["Governance structure", "Transfer restrictions", "Tag/drag rights"]
            }
        ],
        "legal_checklist": [
            "Incorporate your business (LLC or Corporation)",
            "Set up proper equity structure and cap table",
            "Implement employee stock option plan if needed",
            "Ensure compliance with securities regulations",
            "Prepare data room with all legal documents",
            "Review intellectual property ownership",
            "Clear any founder disputes or issues"
        ],
        "compliance_notes": [
            "All fundraising must comply with securities laws",
            "Consider federal and state registration requirements",
            "Accredited investor verification may be required",
            "Maintain detailed records of all communications",
            "Consult qualified legal counsel before proceeding"
        ],
        "recommended_lawyers": [
            {
                "firm": "TechLaw Partners",
                "specialization": "Startup and venture capital law",
                "experience": "15+ years in tech fundraising",
                "typical_fees": "$300-500/hour",
                "contact": "info@techlawpartners.com"
            }
        ]
    }

# Helper functions

def analyze_pitch_with_ai(pitch_practice: PitchPractice) -> Dict[str, Any]:
    """Simulate AI analysis of pitch content"""
    
    # Analyze different aspects of the pitch
    content_analysis = analyze_pitch_content(pitch_practice.pitch_content)
    industry_fit = analyze_industry_context(pitch_practice.industry)
    funding_realism = analyze_funding_request(pitch_practice.target_funding, pitch_practice.industry)
    
    overall_score = (content_analysis['score'] + industry_fit['score'] + funding_realism['score']) / 3
    
    return {
        "overall_score": overall_score,
        "content_analysis": content_analysis,
        "industry_analysis": industry_fit,
        "funding_analysis": funding_realism,
        "strengths": identify_pitch_strengths(pitch_practice),
        "weaknesses": identify_pitch_weaknesses(pitch_practice),
        "specific_recommendations": generate_specific_recommendations(pitch_practice),
        "investor_perspective": simulate_investor_feedback(pitch_practice)
    }

def analyze_pitch_content(content: str) -> Dict[str, Any]:
    """Analyze the content quality of the pitch"""
    word_count = len(content.split())
    
    # Check for key elements
    key_elements = [
        ("problem", ["problem", "challenge", "issue", "pain"]),
        ("solution", ["solution", "solve", "address", "fix"]),
        ("market", ["market", "customers", "users", "target"]),
        ("traction", ["users", "revenue", "growth", "customers"]),
        ("team", ["team", "founder", "experience", "background"])
    ]
    
    elements_present = {}
    for element, keywords in key_elements:
        elements_present[element] = any(keyword in content.lower() for keyword in keywords)
    
    score = sum(elements_present.values()) / len(elements_present) * 100
    
    return {
        "score": score,
        "word_count": word_count,
        "elements_present": elements_present,
        "readability": "Good" if 100 <= word_count <= 500 else "Too short" if word_count < 100 else "Too long",
        "recommendations": [
            "Include clear problem statement" if not elements_present["problem"] else None,
            "Explain your solution clearly" if not elements_present["solution"] else None,
            "Define your target market" if not elements_present["market"] else None,
            "Show traction metrics" if not elements_present["traction"] else None,
            "Introduce your team" if not elements_present["team"] else None
        ]
    }

def analyze_industry_context(industry: str) -> Dict[str, Any]:
    """Analyze industry-specific context"""
    industry_data = {
        "fintech": {"growth_rate": 25, "avg_funding": 500000, "competition": "high"},
        "healthcare": {"growth_rate": 15, "avg_funding": 750000, "competition": "medium"},
        "ecommerce": {"growth_rate": 20, "avg_funding": 300000, "competition": "high"},
        "productivity": {"growth_rate": 18, "avg_funding": 250000, "competition": "medium"},
        "social": {"growth_rate": 30, "avg_funding": 400000, "competition": "high"},
        "gaming": {"growth_rate": 12, "avg_funding": 200000, "competition": "high"}
    }
    
    industry_key = industry.lower()
    if industry_key not in industry_data:
        industry_key = "productivity"  # Default
    
    data = industry_data[industry_key]
    
    score = 85 if data["competition"] == "medium" else 70 if data["competition"] == "high" else 90
    
    return {
        "score": score,
        "growth_rate": data["growth_rate"],
        "average_funding": data["avg_funding"],
        "competition_level": data["competition"],
        "industry_trends": generate_industry_trends(industry),
        "success_factors": generate_industry_success_factors(industry)
    }

def analyze_funding_request(amount: float, industry: str) -> Dict[str, Any]:
    """Analyze if funding request is realistic"""
    industry_averages = {
        "fintech": 500000,
        "healthcare": 750000,
        "ecommerce": 300000,
        "productivity": 250000,
        "social": 400000,
        "gaming": 200000
    }
    
    avg_funding = industry_averages.get(industry.lower(), 300000)
    ratio = amount / avg_funding
    
    if 0.5 <= ratio <= 2.0:
        score = 90
        assessment = "Realistic"
    elif 0.25 <= ratio <= 3.0:
        score = 75
        assessment = "Reasonable"
    else:
        score = 50
        assessment = "May need justification"
    
    return {
        "score": score,
        "assessment": assessment,
        "industry_average": avg_funding,
        "your_request": amount,
        "ratio": ratio,
        "recommendations": generate_funding_recommendations(amount, avg_funding, ratio)
    }

def calculate_app_valuation(inputs: ValuationInputs) -> Dict[str, float]:
    """Calculate app valuation using multiple methods"""
    
    # Revenue multiple method
    industry_multiples = {
        "high": 8,
        "medium": 5,
        "low": 3
    }
    
    competition_multiple = industry_multiples.get(inputs.competition_level, 5)
    revenue_valuation = inputs.annual_revenue * competition_multiple
    
    # DCF method (simplified)
    years = 5
    discount_rate = 0.12
    projected_revenue = inputs.annual_revenue
    dcf_value = 0
    
    for year in range(1, years + 1):
        projected_revenue *= (1 + inputs.growth_rate / 100)
        present_value = projected_revenue / ((1 + discount_rate) ** year)
        dcf_value += present_value
    
    # Market-based method
    market_penetration = min(0.05, inputs.annual_revenue / inputs.market_size) if inputs.market_size > 0 else 0.01
    market_valuation = inputs.market_size * market_penetration * 0.1
    
    # Comparable analysis (simplified)
    experience_multiplier = {"high": 1.3, "medium": 1.1, "low": 0.9}.get(inputs.team_experience, 1.0)
    traction_multiplier = {"strong": 1.4, "medium": 1.2, "early": 1.0}.get(inputs.traction, 1.0)
    
    comparable_valuation = revenue_valuation * experience_multiplier * traction_multiplier
    
    return {
        "revenue_multiple": revenue_valuation,
        "dcf_model": dcf_value,
        "market_based": market_valuation,
        "comparable_analysis": comparable_valuation
    }

def analyze_valuation_factors(inputs: ValuationInputs) -> Dict[str, Any]:
    """Analyze factors affecting valuation"""
    return {
        "revenue_strength": "Strong" if inputs.annual_revenue > 100000 else "Moderate" if inputs.annual_revenue > 50000 else "Early",
        "growth_assessment": "Excellent" if inputs.growth_rate > 50 else "Good" if inputs.growth_rate > 20 else "Moderate",
        "market_opportunity": "Large" if inputs.market_size > 1000000000 else "Medium" if inputs.market_size > 100000000 else "Niche",
        "competitive_position": inputs.competition_level,
        "team_strength": inputs.team_experience,
        "traction_level": inputs.traction,
        "risk_factors": [
            "High competition" if inputs.competition_level == "high" else None,
            "Limited traction" if inputs.traction == "early" else None,
            "Inexperienced team" if inputs.team_experience == "low" else None,
            "Slow growth" if inputs.growth_rate < 10 else None
        ]
    }

def generate_valuation_recommendations(inputs: ValuationInputs, valuations: Dict[str, float]) -> List[str]:
    """Generate valuation recommendations"""
    recommendations = []
    
    avg_valuation = sum(valuations.values()) / len(valuations)
    
    if inputs.growth_rate < 20:
        recommendations.append("Focus on accelerating growth rate to increase valuation")
    
    if inputs.competition_level == "high":
        recommendations.append("Develop unique competitive advantages to justify premium valuation")
    
    if inputs.team_experience == "low":
        recommendations.append("Consider bringing on experienced advisors or team members")
    
    if inputs.annual_revenue < 50000:
        recommendations.append("Increase revenue traction before raising at high valuation")
    
    return recommendations

def generate_detailed_term_sheet_sections(inputs: TermSheetInputs) -> Dict[str, Any]:
    """Generate detailed sections for term sheet"""
    return {
        "investment_summary": f"Investment of ${inputs.investment_amount:,.2f} in {inputs.company_name}",
        "valuation_details": {
            "methodology": "Based on comparable company analysis and DCF model",
            "key_assumptions": ["Market growth rate", "Revenue projections", "Exit timeline"]
        },
        "use_of_funds": [
            "Product development (40%)",
            "Marketing and customer acquisition (30%)",
            "Team expansion (20%)",
            "Working capital (10%)"
        ],
        "milestone_schedule": [
            "Achieve $100K ARR within 12 months",
            "Launch v2.0 product within 18 months",
            "Reach profitability within 24 months"
        ]
    }

def find_matching_investors(category: str, stage: str, amount: float) -> List[Dict[str, Any]]:
    """Find matching investors (simulated)"""
    
    # Simulated investor database
    mock_investors = [
        {
            "name": "TechVentures Capital",
            "focus_areas": ["fintech", "productivity", "saas"],
            "typical_check_size": {"min": 100000, "max": 500000},
            "stage_preference": ["seed", "series_a"],
            "location": "San Francisco, CA",
            "portfolio_size": 45,
            "match_score": 95,
            "contact_info": "partners@techventures.vc",
            "warm_intro_available": True,
            "recent_investments": ["TaskFlow Pro", "DataSync", "CloudManager"]
        },
        {
            "name": "Innovation Partners",
            "focus_areas": ["healthcare", "fintech", "social"],
            "typical_check_size": {"min": 50000, "max": 250000},
            "stage_preference": ["pre_seed", "seed"],
            "location": "Austin, TX",
            "portfolio_size": 32,
            "match_score": 87,
            "contact_info": "info@innovationpartners.com",
            "warm_intro_available": False,
            "recent_investments": ["HealthTracker+", "MedConnect", "WellnessApp"]
        },
        {
            "name": "Growth Capital LLC",
            "focus_areas": ["ecommerce", "marketplace", "consumer"],
            "typical_check_size": {"min": 250000, "max": 1000000},
            "stage_preference": ["series_a", "series_b"],
            "location": "New York, NY",
            "portfolio_size": 28,
            "match_score": 82,
            "contact_info": "deals@growthcapital.com",
            "warm_intro_available": True,
            "recent_investments": ["LocalMarket", "ShopEasy", "DeliveryNow"]
        }
    ]
    
    # Filter and score based on inputs
    matched_investors = []
    for investor in mock_investors:
        score = 0
        
        # Category match
        if category.lower() in [area.lower() for area in investor["focus_areas"]]:
            score += 40
        
        # Stage match
        if stage.lower() in investor["stage_preference"]:
            score += 30
        
        # Check size match
        if investor["typical_check_size"]["min"] <= amount <= investor["typical_check_size"]["max"]:
            score += 30
        
        if score >= 60:  # Minimum match threshold
            investor["match_score"] = score
            matched_investors.append(investor)
    
    return sorted(matched_investors, key=lambda x: x["match_score"], reverse=True)

def generate_outreach_recommendations(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate outreach recommendations"""
    return {
        "prioritization": "Focus on investors with warm intro opportunities first",
        "timing": "Best to reach out Tuesday-Thursday, 9-11 AM",
        "approach": [
            "Research investor's recent investments",
            "Personalize your outreach message",
            "Include key metrics in subject line",
            "Keep initial email under 150 words",
            "Follow up after 1 week if no response"
        ],
        "success_rates": {
            "warm_intro": "35-45%",
            "cold_outreach": "5-10%",
            "conference_meetings": "20-30%"
        }
    }

def generate_introduction_templates() -> Dict[str, str]:
    """Generate email templates for investor outreach"""
    return {
        "cold_outreach": """
Subject: [Company Name] - $[Amount] raise, [Key Metric]

Hi [Investor Name],

I'm [Your Name], founder of [Company Name]. We're raising $[Amount] to [Brief Use of Funds].

Quick traction snapshot:
• [Key Metric 1]
• [Key Metric 2]  
• [Key Metric 3]

We're solving [Problem] for [Target Market] with [Solution]. I'd love to send you our deck and discuss how this fits your portfolio.

Best,
[Your Name]
        """,
        "warm_intro_request": """
Subject: Introduction request - [Company Name] fundraising

Hi [Mutual Connection],

Hope you're well! I'm reaching out because I know you have a relationship with [Investor Name] at [Firm].

We're raising $[Amount] for [Company Name], and [Investor] seems like a great fit based on their investments in [Similar Company]. 

Would you be comfortable making an introduction? Happy to send you our deck and any other materials you'd need.

Thanks!
[Your Name]
        """,
        "follow_up": """
Subject: Re: [Company Name] - Quick update

Hi [Investor Name],

Following up on my note from last week about [Company Name].

Quick update since then:
• [Recent Achievement/Milestone]
• [Progress Update]

Still interested in sharing our deck if you have bandwidth for new deals.

Best,
[Your Name]
        """
    }

# Additional helper functions for content generation
def identify_pitch_strengths(pitch: PitchPractice) -> List[str]:
    """Identify strengths in the pitch"""
    strengths = []
    content = pitch.pitch_content.lower()
    
    if any(word in content for word in ["revenue", "customers", "users", "growth"]):
        strengths.append("Shows concrete traction metrics")
    
    if any(word in content for word in ["team", "experience", "background"]):
        strengths.append("Addresses team qualifications")
    
    if any(word in content for word in ["market", "opportunity", "size"]):
        strengths.append("Discusses market opportunity")
    
    if len(pitch.pitch_content.split()) > 100:
        strengths.append("Comprehensive pitch content")
    
    return strengths or ["Shows initiative in pitch preparation"]

def identify_pitch_weaknesses(pitch: PitchPractice) -> List[str]:
    """Identify weaknesses in the pitch"""
    weaknesses = []
    content = pitch.pitch_content.lower()
    
    if not any(word in content for word in ["problem", "challenge", "issue"]):
        weaknesses.append("Missing clear problem statement")
    
    if not any(word in content for word in ["competition", "competitive", "differentiate"]):
        weaknesses.append("Doesn't address competitive landscape")
    
    if not any(word in content for word in ["business model", "monetize", "revenue"]):
        weaknesses.append("Unclear business model")
    
    if len(pitch.pitch_content.split()) < 50:
        weaknesses.append("Pitch content too brief")
    
    return weaknesses or ["Consider adding more specific metrics"]

def generate_specific_recommendations(pitch: PitchPractice) -> List[str]:
    """Generate specific recommendations for improvement"""
    recommendations = []
    
    recommendations.append(f"For {pitch.industry} apps, emphasize regulatory compliance and data security")
    recommendations.append("Include a clear competitive analysis section")
    recommendations.append("Add specific financial projections for next 3 years")
    recommendations.append("Mention your go-to-market strategy")
    recommendations.append("Include customer testimonials or case studies")
    
    return recommendations

def simulate_investor_feedback(pitch: PitchPractice) -> Dict[str, str]:
    """Simulate different investor perspectives"""
    return {
        "early_stage_vc": "Focus more on market size and scalability potential",
        "angel_investor": "Great to see founder passion, but need clearer path to profitability",
        "strategic_investor": "How does this fit into existing market ecosystem?",
        "accelerator": "Strong concept, but needs more customer validation"
    }

def generate_industry_trends(industry: str) -> List[str]:
    """Generate industry-specific trends"""
    trends = {
        "fintech": ["Open banking adoption", "AI-powered financial services", "Regulatory technology growth"],
        "healthcare": ["Telemedicine expansion", "AI diagnostics", "Patient data portability"],
        "ecommerce": ["Social commerce", "Sustainability focus", "AR/VR shopping experiences"],
        "productivity": ["Remote work tools", "AI automation", "Collaborative platforms"],
        "social": ["Creator economy", "Privacy-focused platforms", "Audio-based social media"],
        "gaming": ["Mobile gaming dominance", "Cloud gaming", "NFT integration"]
    }
    
    return trends.get(industry.lower(), ["Digital transformation", "Mobile-first approach", "Data-driven insights"])

def generate_industry_success_factors(industry: str) -> List[str]:
    """Generate industry-specific success factors"""
    factors = {
        "fintech": ["Regulatory compliance", "Security", "User trust", "Integration capabilities"],
        "healthcare": ["Clinical validation", "Privacy compliance", "Provider partnerships", "Evidence-based outcomes"],
        "ecommerce": ["User experience", "Logistics efficiency", "Payment processing", "Customer acquisition cost"],
        "productivity": ["Workflow integration", "User adoption", "ROI measurement", "Scalability"],
        "social": ["Network effects", "User engagement", "Content moderation", "Viral growth"],
        "gaming": ["Gameplay mechanics", "Monetization balance", "Community building", "Platform optimization"]
    }
    
    return factors.get(industry.lower(), ["Product-market fit", "User acquisition", "Retention", "Monetization"])

def generate_funding_recommendations(amount: float, avg: float, ratio: float) -> List[str]:
    """Generate funding amount recommendations"""
    recommendations = []
    
    if ratio > 2:
        recommendations.append("Consider if this amount is necessary for initial milestones")
        recommendations.append("Break funding into smaller rounds")
    elif ratio < 0.5:
        recommendations.append("Ensure funding is sufficient for 18-24 months runway")
        recommendations.append("Consider if additional funding will be needed soon")
    
    recommendations.append("Justify funding amount with detailed use of funds breakdown")
    recommendations.append("Show how this funding leads to next milestone or profitability")
    
    return recommendations

def generate_improvement_plan(feedback: Dict[str, Any]) -> List[str]:
    """Generate improvement plan based on feedback"""
    plan = []
    
    if feedback['overall_score'] < 70:
        plan.append("Focus on strengthening core pitch elements")
        plan.append("Practice pitch delivery with timing")
    
    if 'problem' not in feedback['content_analysis']['elements_present']:
        plan.append("Develop compelling problem statement with data")
    
    if 'solution' not in feedback['content_analysis']['elements_present']:
        plan.append("Clearly articulate your unique solution")
    
    plan.append("Prepare for common investor questions")
    plan.append("Create supporting materials (demo, financial model)")
    
    return plan