#!/usr/bin/env python3

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

router = APIRouter()

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('trading_legal.db')

# Pydantic models
class ReadinessAssessment(BaseModel):
    user_id: str
    experience_level: str
    risk_tolerance: str
    financial_knowledge_score: int
    available_capital: float
    investment_goals: List[str]
    time_horizon: str

class BrokerComparison(BaseModel):
    min_balance: float
    commission_importance: str
    platform_features: List[str]
    account_types: List[str]
    geographic_location: str

# Assessment endpoints
@router.post("/assess-readiness")
async def assess_trading_readiness(assessment: ReadinessAssessment):
    """Assess user's readiness to transition from paper to real trading"""
    
    # Calculate overall readiness score (0-100)
    base_score = 0
    
    # Experience level scoring
    experience_scores = {
        'beginner': 10,
        'novice': 25,
        'intermediate': 50,
        'advanced': 75,
        'expert': 90
    }
    base_score += experience_scores.get(assessment.experience_level, 10)
    
    # Risk tolerance consideration (moderate risk tolerance gets highest score)
    risk_scores = {
        'very_conservative': 15,
        'conservative': 25,
        'moderate': 35,
        'aggressive': 25,
        'very_aggressive': 15
    }
    base_score += risk_scores.get(assessment.risk_tolerance, 15)
    
    # Financial knowledge score (directly weighted)
    base_score += min(assessment.financial_knowledge_score * 0.3, 30)
    
    # Capital adequacy (minimum $1000 recommended)
    if assessment.available_capital >= 10000:
        capital_score = 25
    elif assessment.available_capital >= 5000:
        capital_score = 20
    elif assessment.available_capital >= 1000:
        capital_score = 15
    elif assessment.available_capital >= 500:
        capital_score = 10
    else:
        capital_score = 5
    base_score += capital_score
    
    # Time horizon consideration
    horizon_scores = {
        'short_term': 10,    # <1 year
        'medium_term': 20,   # 1-5 years
        'long_term': 25      # >5 years
    }
    base_score += horizon_scores.get(assessment.time_horizon, 15)
    
    # Cap at 100
    overall_score = min(base_score, 100)
    
    # Generate recommendations based on score
    recommendations = []
    warnings = []
    
    if overall_score < 40:
        recommendations.extend([
            "Complete additional educational courses",
            "Practice with paper trading for at least 3 more months",
            "Build larger emergency fund before investing",
            "Consider starting with index funds or ETFs"
        ])
        warnings.extend([
            "High risk of significant losses",
            "Insufficient experience for active trading",
            "Consider professional financial advice"
        ])
    elif overall_score < 60:
        recommendations.extend([
            "Start with small positions (< $500 per trade)",
            "Focus on blue-chip stocks initially",
            "Set strict stop-loss limits",
            "Continue education on risk management"
        ])
        warnings.extend([
            "Start slowly and build experience gradually",
            "Avoid options and leveraged products initially"
        ])
    elif overall_score < 80:
        recommendations.extend([
            "Consider diversified portfolio approach",
            "Gradually increase position sizes",
            "Explore different asset classes cautiously",
            "Implement proper risk management strategies"
        ])
        warnings.extend([
            "Monitor positions closely",
            "Be prepared for market volatility"
        ])
    else:
        recommendations.extend([
            "Well-prepared for real trading",
            "Consider advanced strategies carefully",
            "Maintain disciplined risk management",
            "Regular portfolio review and rebalancing"
        ])
    
    # Recommend suitable brokers based on profile
    recommended_brokers = []
    if assessment.available_capital < 1000:
        recommended_brokers.extend(['robinhood', 'webull'])
    elif assessment.available_capital < 10000:
        recommended_brokers.extend(['td_ameritrade', 'charles_schwab', 'fidelity'])
    else:
        recommended_brokers.extend(['interactive_brokers', 'td_ameritrade', 'charles_schwab'])
    
    # Store assessment in database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO transition_readiness
        (user_id, overall_score, risk_assessment_score, knowledge_assessment_score, 
         experience_level, recommended_brokers, warnings)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (assessment.user_id, overall_score, assessment.risk_tolerance, 
          assessment.financial_knowledge_score, assessment.experience_level,
          json.dumps(recommended_brokers), json.dumps(warnings)))
    
    conn.commit()
    conn.close()
    
    return {
        "overall_readiness_score": overall_score,
        "readiness_level": "ready" if overall_score >= 70 else "needs_preparation" if overall_score >= 50 else "not_ready",
        "recommendations": recommendations,
        "warnings": warnings,
        "recommended_brokers": recommended_brokers,
        "assessment_date": datetime.now(),
        "next_assessment_recommended": datetime.now() + timedelta(days=30)
    }

@router.get("/broker-comparison")
async def get_broker_comparison(
    min_balance: float = 0,
    region: str = "US",
    account_type: str = "individual"
):
    """Get detailed broker comparison based on user requirements"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get brokers from database
    cursor.execute('''
        SELECT * FROM broker_integrations 
        WHERE minimum_balance <= ? 
        AND json_extract(supported_regions, '$[0]') LIKE ?
        ORDER BY is_recommended DESC, risk_level ASC
    ''', (min_balance, f"%{region}%"))
    
    brokers = cursor.fetchall()
    conn.close()
    
    broker_details = []
    for broker in brokers:
        broker_info = {
            "broker_id": broker[0],
            "name": broker[1],
            "api_status": broker[2],
            "supported_regions": json.loads(broker[3]) if broker[3] else [],
            "minimum_balance": broker[4],
            "commission_structure": json.loads(broker[5]) if broker[5] else {},
            "features": json.loads(broker[6]) if broker[6] else [],
            "integration_guide": broker[7],
            "is_recommended": broker[8],
            "risk_level": broker[9],
            "pros": [],
            "cons": [],
            "best_for": []
        }
        
        # Add specific pros/cons for each broker
        if broker[0] == 'td_ameritrade':
            broker_info.update({
                "pros": ["Excellent research tools", "No commission on stocks/ETFs", "thinkorswim platform", "24/7 support"],
                "cons": ["$500 minimum for margin", "Limited international markets"],
                "best_for": ["Beginners to intermediate traders", "Options trading", "Research-focused investors"]
            })
        elif broker[0] == 'interactive_brokers':
            broker_info.update({
                "pros": ["Lowest fees", "Global markets", "Professional tools", "Advanced order types"],
                "cons": ["Complex platform", "$10/month fee if < $100k", "Not beginner-friendly"],
                "best_for": ["Active traders", "International investing", "Advanced strategies"]
            })
        elif broker[0] == 'robinhood':
            broker_info.update({
                "pros": ["Mobile-first design", "Zero commissions", "Fractional shares", "Crypto trading"],
                "cons": ["Limited research tools", "No phone support", "Basic platform features"],
                "best_for": ["Young investors", "Mobile-only users", "Casual traders"]
            })
        
        broker_details.append(broker_info)
    
    return {
        "brokers": broker_details,
        "comparison_factors": [
            "Commission structure",
            "Account minimums", 
            "Available research",
            "Platform features",
            "Customer support",
            "Investment options",
            "Educational resources"
        ],
        "selection_guide": {
            "beginners": "Focus on educational resources and ease of use",
            "active_traders": "Look for advanced tools and low fees",
            "long_term_investors": "Prioritize research tools and low expense ratios",
            "international_investors": "Ensure global market access"
        }
    }

@router.get("/tax-education")
async def get_tax_education():
    """Provide tax education for real trading transition"""
    
    return {
        "tax_basics": {
            "capital_gains_vs_losses": {
                "short_term": "Held < 1 year - taxed as ordinary income",
                "long_term": "Held > 1 year - preferential tax rates (0%, 15%, 20%)",
                "wash_sale_rule": "Cannot claim loss if you buy same security within 30 days"
            },
            "tax_advantaged_accounts": {
                "traditional_ira": {
                    "contribution_limit_2024": 7000,
                    "catch_up_limit_50plus": 1000,
                    "tax_treatment": "Tax-deductible contributions, taxed on withdrawal"
                },
                "roth_ira": {
                    "contribution_limit_2024": 7000,
                    "income_limits": "Phases out for high earners",
                    "tax_treatment": "After-tax contributions, tax-free growth and withdrawals"
                },
                "401k": {
                    "contribution_limit_2024": 23000,
                    "employer_match": "Often available - free money!",
                    "vesting_schedules": "May have waiting periods"
                }
            }
        },
        "record_keeping": {
            "required_records": [
                "Purchase and sale confirmations",
                "Dividend and interest statements", 
                "Brokerage account statements",
                "Wash sale adjustments",
                "Cost basis information"
            ],
            "recommended_tools": [
                "TurboTax Premier",
                "H&R Block Premium",
                "TaxAct Premier",
                "Professional tax software"
            ],
            "retention_period": "Keep records for at least 3 years after filing, 7 years for large losses"
        },
        "tax_strategies": {
            "tax_loss_harvesting": "Sell losing investments to offset gains",
            "asset_location": "Put tax-inefficient investments in tax-advantaged accounts",
            "hold_periods": "Consider waiting for long-term capital gains treatment",
            "timing": "Be strategic about when you realize gains and losses"
        },
        "common_mistakes": [
            "Not tracking cost basis properly",
            "Violating wash sale rules",
            "Forgetting about dividend reinvestments",
            "Not considering state taxes",
            "Missing required distributions from retirement accounts"
        ],
        "resources": [
            "IRS Publication 550 - Investment Income and Expenses",
            "IRS Publication 564 - Mutual Fund Distributions", 
            "Consult a tax professional for complex situations",
            "Use broker tax tools and cost basis tracking"
        ]
    }

@router.get("/risk-warnings")
async def get_risk_warnings():
    """Comprehensive risk warnings for real trading"""
    
    return {
        "market_risks": {
            "market_volatility": {
                "description": "Stock prices can fluctuate dramatically",
                "examples": ["2008 financial crisis: -37% market drop", "COVID-19 2020: -34% then +68%"],
                "mitigation": "Diversification, dollar-cost averaging, long investment horizons"
            },
            "sector_concentration": {
                "description": "Over-investing in one industry increases risk",
                "examples": ["Tech bubble 2000", "Energy sector 2014-2016"],
                "mitigation": "Spread investments across sectors and geographies"
            },
            "company_specific": {
                "description": "Individual companies can fail completely",
                "examples": ["Enron", "Lehman Brothers", "WorldCom"],
                "mitigation": "Never invest more than 5-10% in any single stock"
            }
        },
        "behavioral_risks": {
            "emotional_trading": {
                "fear_and_greed": "Can lead to buying high and selling low",
                "overconfidence": "Early success can lead to excessive risk-taking",
                "loss_aversion": "Holding losing positions too long"
            },
            "cognitive_biases": [
                "Confirmation bias - seeking information that confirms beliefs",
                "Anchoring - relying too heavily on first information received",
                "Herd mentality - following the crowd",
                "Recency bias - overweighting recent events"
            ]
        },
        "trading_specific_risks": {
            "leverage_and_margin": {
                "description": "Borrowing to invest amplifies both gains and losses",
                "warnings": ["Can lose more than initial investment", "Forced liquidation in margin calls"],
                "recommendation": "Avoid leverage until very experienced"
            },
            "options_trading": {
                "description": "Complex derivatives with time decay",
                "warnings": ["Can expire worthless", "Unlimited loss potential with some strategies"],
                "recommendation": "Extensive education required before trading options"
            },
            "day_trading": {
                "description": "Buying and selling within same day",
                "statistics": "80% of day traders lose money",
                "requirements": "$25,000 minimum for pattern day trading"
            }
        },
        "external_risks": {
            "inflation": "Erodes purchasing power over time",
            "interest_rate_changes": "Affects bond prices and stock valuations",
            "geopolitical_events": "Wars, elections, trade disputes affect markets",
            "regulatory_changes": "New laws can impact specific sectors"
        },
        "risk_management_strategies": {
            "position_sizing": "Never risk more than 1-2% of portfolio on single trade",
            "stop_losses": "Set predetermined exit points for losing trades",
            "diversification": "Spread risk across assets, sectors, and time",
            "emergency_fund": "Keep 3-6 months expenses in cash before investing",
            "regular_review": "Monitor and rebalance portfolio quarterly"
        },
        "warning_signs": [
            "Borrowing money to invest",
            "Investing money needed within 5 years",
            "Making trades based on tips or rumors",
            "Feeling you need to 'make back' losses quickly",
            "Checking portfolio multiple times per day",
            "Losing sleep over investments"
        ],
        "when_to_seek_help": [
            "Consistent losses over 6+ months",
            "Investing affecting personal relationships",
            "Unable to stick to predetermined strategy",
            "Complex financial situations requiring expertise"
        ]
    }

@router.post("/broker-integration-prep")
async def prepare_broker_integration(user_id: str, preferred_broker: str):
    """Prepare user for broker account setup and integration"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get broker details
    cursor.execute('SELECT * FROM broker_integrations WHERE broker_id = ?', (preferred_broker,))
    broker = cursor.fetchone()
    
    if not broker:
        raise HTTPException(status_code=404, detail="Broker not found")
    
    # Get user readiness assessment
    cursor.execute('SELECT * FROM transition_readiness WHERE user_id = ?', (user_id,))
    readiness = cursor.fetchone()
    
    conn.close()
    
    preparation_steps = {
        "account_setup": {
            "required_documents": [
                "Government-issued photo ID (driver's license, passport)",
                "Social Security number or Tax ID",
                "Bank account information for funding",
                "Employment information",
                "Financial information (income, net worth, investment experience)"
            ],
            "account_types": {
                "individual_taxable": "Standard brokerage account",
                "individual_retirement": "IRA for tax advantages",
                "joint_account": "Shared account with spouse/partner",
                "custodial_account": "For minors (UGMA/UTMA)"
            }
        },
        "funding_options": [
            "ACH bank transfer (3-5 business days, usually free)",
            "Wire transfer (same day, $25-30 fee typical)",
            "Check deposit (5-10 business days)",
            "ACAT transfer from another broker (5-10 business days)"
        ],
        "initial_steps": [
            f"Visit {broker[1]} website and start account application",
            "Complete identity verification process",
            "Fund account with initial deposit",
            "Familiarize yourself with trading platform",
            "Start with small positions to test the system",
            "Set up account alerts and notifications"
        ],
        "platform_features": json.loads(broker[6]) if broker[6] else [],
        "commission_structure": json.loads(broker[5]) if broker[5] else {},
        "integration_timeline": {
            "week_1": "Account opening and funding",
            "week_2": "Platform familiarization and paper trading",
            "week_3": "First small trades with real money",
            "month_2": "Gradual position sizing increase",
            "month_3": "Full strategy implementation"
        }
    }
    
    if readiness and readiness[1] < 60:  # Low readiness score
        preparation_steps["additional_education"] = [
            "Complete at least 2 more trading courses",
            "Practice with paper trading for 30 more days",
            "Read recommended investment books",
            "Consider starting with robo-advisor instead"
        ]
    
    return {
        "broker_name": broker[1],
        "preparation_checklist": preparation_steps,
        "estimated_setup_time": "1-2 weeks",
        "recommended_initial_deposit": max(broker[4], 1000),  # Minimum balance or $1000
        "support_resources": {
            "customer_service": "Available during market hours",
            "educational_resources": "Webinars, tutorials, market research",
            "community": "User forums and social trading features"
        },
        "next_steps": [
            "Complete broker readiness assessment",
            "Gather required documents", 
            "Start account application process",
            "Schedule follow-up consultation"
        ]
    }

@router.get("/regulatory-requirements")
async def get_regulatory_requirements():
    """Get regulatory requirements for different trading activities"""
    
    return {
        "pattern_day_trading": {
            "definition": "4+ day trades in 5 business days",
            "requirements": {
                "minimum_equity": 25000,
                "currency": "USD",
                "account_type": "Margin account required"
            },
            "restrictions": "Limited to 3x buying power",
            "violations": "Account restrictions if requirements not met"
        },
        "margin_trading": {
            "definition": "Trading with borrowed funds from broker",
            "initial_requirement": "50% of purchase price",
            "maintenance_requirement": "25% minimum (varies by broker)",
            "risks": ["Amplified losses", "Margin calls", "Forced liquidation"]
        },
        "options_trading": {
            "approval_levels": {
                "level_1": "Covered calls and cash-secured puts",
                "level_2": "Long calls and puts",
                "level_3": "Spreads and combinations", 
                "level_4": "Naked options writing"
            },
            "requirements": "Options agreement and suitability assessment"
        },
        "international_considerations": {
            "foreign_tax_withholding": "May apply to international investments",
            "currency_exchange": "Additional costs for foreign securities",
            "regulatory_differences": "Different rules in different countries",
            "reporting_requirements": "FATCA and other international reporting"
        },
        "record_keeping_requirements": {
            "trade_confirmations": "Keep all purchase and sale records",
            "account_statements": "Monthly and annual statements",
            "tax_documents": "1099s and other tax reporting forms",
            "retention_period": "At least 3 years, 7 years recommended"
        },
        "investor_protections": {
            "sipc_insurance": "Up to $500,000 per account ($250,000 cash)",
            "fdic_insurance": "Cash balances may be FDIC insured",
            "arbitration": "FINRA arbitration for disputes",
            "compliance": "Brokers must follow suitability requirements"
        }
    }

@router.get("/transition-timeline/{user_id}")
async def get_transition_timeline(user_id: str):
    """Get personalized transition timeline from paper to real trading"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user readiness data
    cursor.execute('SELECT * FROM transition_readiness WHERE user_id = ?', (user_id,))
    readiness = cursor.fetchone()
    
    conn.close()
    
    if not readiness:
        base_timeline = 12  # weeks
        readiness_score = 30
    else:
        readiness_score = readiness[1]
        
    # Adjust timeline based on readiness score
    if readiness_score >= 80:
        base_timeline = 4   # weeks
    elif readiness_score >= 60:
        base_timeline = 8   # weeks
    else:
        base_timeline = 16  # weeks
    
    timeline = {
        "total_duration_weeks": base_timeline,
        "readiness_score": readiness_score,
        "phases": []
    }
    
    # Phase 1: Preparation (always 2-4 weeks)
    prep_weeks = min(4, max(2, base_timeline // 4))
    timeline["phases"].append({
        "phase": 1,
        "name": "Preparation & Education",
        "duration_weeks": prep_weeks,
        "goals": [
            "Complete advanced trading courses",
            "Master risk management principles", 
            "Understand tax implications",
            "Research and select broker"
        ],
        "activities": [
            "Study market analysis techniques",
            "Practice with advanced paper trading",
            "Complete broker comparison research",
            "Gather account opening documents"
        ],
        "milestones": [
            "Pass advanced trading assessment (80%+)",
            "Complete tax education module",
            "Select preferred broker",
            "Prepare required documentation"
        ]
    })
    
    # Phase 2: Account Setup (1-2 weeks)
    setup_weeks = 2 if readiness_score < 60 else 1
    timeline["phases"].append({
        "phase": 2,
        "name": "Account Setup & Funding",
        "duration_weeks": setup_weeks,
        "goals": [
            "Open brokerage account",
            "Complete verification process",
            "Fund account appropriately",
            "Familiarize with platform"
        ],
        "activities": [
            "Submit account application",
            "Complete identity verification",
            "Make initial deposit",
            "Explore trading platform features"
        ],
        "milestones": [
            "Account approved and active",
            "Funds available for trading",
            "Platform tutorial completed",
            "First practice trade executed"
        ]
    })
    
    # Phase 3: Gradual Transition
    transition_weeks = base_timeline - prep_weeks - setup_weeks - 1
    timeline["phases"].append({
        "phase": 3,
        "name": "Gradual Real Trading",
        "duration_weeks": transition_weeks,
        "goals": [
            "Execute first real trades",
            "Gradually increase position sizes",
            "Apply risk management rules",
            "Monitor emotional responses"
        ],
        "activities": [
            "Start with micro-positions (<$100)",
            "Focus on liquid, well-known stocks",
            "Keep detailed trading journal",
            "Review performance weekly"
        ],
        "milestones": [
            "Complete 10 successful small trades",
            "Demonstrate consistent risk management",
            "Show emotional discipline",
            "Achieve positive risk-adjusted returns"
        ]
    })
    
    # Phase 4: Full Implementation
    timeline["phases"].append({
        "phase": 4,
        "name": "Full Strategy Implementation", 
        "duration_weeks": 1,
        "goals": [
            "Implement full trading strategy",
            "Scale to target position sizes",
            "Establish routine monitoring",
            "Plan ongoing education"
        ],
        "activities": [
            "Execute complete investment strategy",
            "Scale positions to comfortable levels",
            "Set up regular portfolio reviews",
            "Join trading communities"
        ],
        "milestones": [
            "Full strategy operational",
            "Consistent with risk parameters",
            "Regular review schedule established",
            "Continued learning plan in place"
        ]
    })
    
    # Add warnings based on readiness score
    if readiness_score < 50:
        timeline["warnings"] = [
            "Consider extending preparation phase",
            "Start with even smaller positions",
            "Consider robo-advisor as alternative",
            "Seek professional guidance"
        ]
    
    timeline["success_metrics"] = [
        "Consistent adherence to risk management rules",
        "Emotional discipline during market volatility",
        "Positive risk-adjusted returns over 6 months",
        "Continuous learning and improvement"
    ]
    
    return timeline