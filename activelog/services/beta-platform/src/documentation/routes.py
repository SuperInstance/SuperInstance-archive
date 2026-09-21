from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from ..database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def get_documentation_home(request: Request):
    """Beta platform documentation home"""
    return templates.TemplateResponse("docs/index.html", {
        "request": request,
        "title": "Beta Platform Documentation"
    })

@router.get("/api-docs")
async def get_api_documentation():
    """Get API documentation"""
    return {
        "title": "ActiveLog Beta Platform API",
        "version": "1.0.0",
        "endpoints": {
            "feedback": {
                "description": "User feedback collection endpoints",
                "endpoints": {
                    "POST /api/feedback/submit": "Submit new feedback",
                    "GET /api/feedback/": "Get feedback list",
                    "GET /api/feedback/{id}": "Get specific feedback",
                    "PUT /api/feedback/{id}/status": "Update feedback status",
                    "GET /api/feedback/stats/summary": "Get feedback statistics"
                }
            },
            "bugs": {
                "description": "Bug reporting with screenshot support",
                "endpoints": {
                    "POST /api/bugs/submit": "Submit bug report with screenshots",
                    "GET /api/bugs/": "Get bug reports",
                    "GET /api/bugs/{id}": "Get specific bug report",
                    "PUT /api/bugs/{id}/status": "Update bug status",
                    "GET /api/bugs/stats/summary": "Get bug statistics"
                }
            },
            "features": {
                "description": "Feature request and voting system",
                "endpoints": {
                    "POST /api/features/submit": "Submit feature request",
                    "GET /api/features/": "Get feature requests",
                    "POST /api/features/{id}/vote": "Vote on feature",
                    "GET /api/features/{id}/votes": "Get vote details",
                    "PUT /api/features/{id}/status": "Update feature status"
                }
            },
            "rewards": {
                "description": "Beta tester rewards and points system",
                "endpoints": {
                    "POST /api/rewards/award": "Award points to user",
                    "GET /api/rewards/user/{id}/balance": "Get user point balance",
                    "GET /api/rewards/leaderboard": "Get rewards leaderboard",
                    "GET /api/rewards/tiers": "Get reward tiers info",
                    "POST /api/rewards/redeem": "Redeem points for rewards"
                }
            },
            "rollout": {
                "description": "Staged rollout management",
                "endpoints": {
                    "POST /api/rollout/stages": "Create rollout stage",
                    "GET /api/rollout/stages": "Get rollout stages",
                    "PUT /api/rollout/stages/{id}/activate": "Activate stage",
                    "GET /api/rollout/user/{id}/features": "Get user features"
                }
            },
            "monitoring": {
                "description": "Performance monitoring",
                "endpoints": {
                    "POST /api/monitoring/performance": "Record performance metric",
                    "GET /api/monitoring/performance/stats": "Get performance stats"
                }
            },
            "crashes": {
                "description": "Crash reporting system",
                "endpoints": {
                    "POST /api/crashes/submit": "Submit crash report",
                    "GET /api/crashes/": "Get crash reports",
                    "GET /api/crashes/stats": "Get crash statistics"
                }
            },
            "analytics": {
                "description": "Usage analytics tracking",
                "endpoints": {
                    "POST /api/analytics/track": "Track usage event",
                    "GET /api/analytics/events": "Get usage events",
                    "GET /api/analytics/stats": "Get usage statistics"
                }
            },
            "ab-testing": {
                "description": "A/B testing framework",
                "endpoints": {
                    "POST /api/ab-testing/tests": "Create A/B test",
                    "GET /api/ab-testing/tests": "Get A/B tests",
                    "POST /api/ab-testing/tests/{id}/start": "Start test",
                    "GET /api/ab-testing/tests/{id}/assign/{user_id}": "Assign user to variant",
                    "POST /api/ab-testing/tests/{id}/results": "Record test result",
                    "GET /api/ab-testing/tests/{id}/analysis": "Get test analysis"
                }
            }
        }
    }

@router.get("/getting-started")
async def get_getting_started_guide():
    """Getting started guide for beta testers"""
    return {
        "title": "Getting Started with ActiveLog Beta",
        "sections": [
            {
                "title": "Welcome to Beta Testing",
                "content": "Thank you for joining the ActiveLog beta program! Your feedback helps us build better software."
            },
            {
                "title": "How to Provide Feedback",
                "content": "Use the feedback form to share your thoughts on UI, performance, features, or general experience.",
                "steps": [
                    "Navigate to the feedback section",
                    "Choose a category (UI, Performance, Feature, General)",
                    "Rate your experience (1-5 stars)",
                    "Provide detailed description",
                    "Submit your feedback"
                ]
            },
            {
                "title": "Reporting Bugs",
                "content": "Help us identify and fix issues by reporting bugs with detailed information.",
                "steps": [
                    "Describe the issue clearly",
                    "Provide steps to reproduce",
                    "Explain expected vs actual behavior", 
                    "Attach screenshots if possible",
                    "Include browser/device information"
                ]
            },
            {
                "title": "Feature Requests",
                "content": "Suggest new features and vote on requests from other users.",
                "steps": [
                    "Check existing requests first",
                    "Submit detailed feature description",
                    "Vote on features you want to see",
                    "Participate in feature discussions"
                ]
            },
            {
                "title": "Earning Rewards",
                "content": "Earn points for beta testing activities and unlock rewards.",
                "rewards": {
                    "Feedback submission": "10 points",
                    "Bug report": "25 points", 
                    "Feature request": "15 points",
                    "Testing session": "50 points",
                    "Community help": "5 points"
                }
            }
        ]
    }

@router.get("/faq")
async def get_faq():
    """Frequently asked questions"""
    return {
        "title": "Beta Platform FAQ",
        "questions": [
            {
                "question": "How do I join the beta program?",
                "answer": "Beta access is currently by invitation only. Contact our team to request access."
            },
            {
                "question": "What browsers are supported?",
                "answer": "We support the latest versions of Chrome, Firefox, Safari, and Edge."
            },
            {
                "question": "How are reward points calculated?",
                "answer": "Points are awarded based on activity type: feedback (10pts), bugs (25pts), features (15pts), testing sessions (50pts)."
            },
            {
                "question": "Can I redeem points for rewards?",
                "answer": "Yes! Points can be redeemed for various rewards including beta tier upgrades and exclusive features."
            },
            {
                "question": "How long does beta testing last?",
                "answer": "Beta testing duration varies by feature. You'll be notified when features graduate to production."
            },
            {
                "question": "Is my data safe during beta testing?",
                "answer": "Yes, we follow strict security and privacy protocols. Beta data is kept separate from production."
            }
        ]
    }