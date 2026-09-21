#!/usr/bin/env python3
"""
Chatbot Configuration Assistant for Adaptive UX System

This module provides natural language configuration assistance, allowing users
to set up complex systems through conversational interfaces with intelligent
recommendations and explanations.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple, Union
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

# Import from other modules
from interface_intelligence import (
    UserProfile, DeviceCapabilityDetector, ExpertiseLevel, 
    InteractionContext, InterfaceIntelligence
)
from progressive_disclosure import ProgressiveDisclosureEngine, FeatureComplexity

class ConversationState(Enum):
    """Current state of the configuration conversation"""
    GREETING = "greeting"
    INTENT_DISCOVERY = "intent_discovery"
    REQUIREMENT_GATHERING = "requirement_gathering"
    HARDWARE_ANALYSIS = "hardware_analysis"
    OPTION_PRESENTATION = "option_presentation"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    COMPLETION = "completion"
    TROUBLESHOOTING = "troubleshooting"

class IntentType(Enum):
    """Types of user intents the assistant can handle"""
    SETUP_NEW_SYSTEM = "setup_new_system"
    OPTIMIZE_EXISTING = "optimize_existing"
    TROUBLESHOOT_ISSUE = "troubleshoot_issue"
    LEARN_FEATURES = "learn_features"
    COMPARE_OPTIONS = "compare_options"
    GET_RECOMMENDATIONS = "get_recommendations"
    UNDERSTAND_HARDWARE = "understand_hardware"
    COST_ANALYSIS = "cost_analysis"

class ResponseType(Enum):
    """Types of assistant responses"""
    QUESTION = "question"
    EXPLANATION = "explanation"
    RECOMMENDATION = "recommendation"
    CONFIRMATION = "confirmation"
    WARNING = "warning"
    CELEBRATION = "celebration"
    INSTRUCTION = "instruction"

@dataclass
class UserIntent:
    """Represents a detected user intent"""
    intent_type: IntentType
    confidence: float
    parameters: Dict[str, Any]
    context: Optional[str] = None

@dataclass
class ConversationContext:
    """Context for the current conversation"""
    user_id: str
    session_id: str
    state: ConversationState
    intent: Optional[UserIntent] = None
    gathered_requirements: Dict[str, Any] = None
    hardware_info: Dict[str, Any] = None
    current_question: Optional[str] = None
    question_attempts: int = 0
    max_question_attempts: int = 3
    
    def __post_init__(self):
        if self.gathered_requirements is None:
            self.gathered_requirements = {}

@dataclass
class AssistantResponse:
    """Response from the chatbot assistant"""
    response_type: ResponseType
    message: str
    options: Optional[List[Dict[str, Any]]] = None
    next_question: Optional[str] = None
    configuration_data: Optional[Dict[str, Any]] = None
    requires_confirmation: bool = False

@dataclass
class ConfigurationTemplate:
    """Template for common configuration scenarios"""
    template_id: str
    name: str
    description: str
    use_cases: List[str]
    required_hardware: Dict[str, Any]
    recommended_settings: Dict[str, Any]
    performance_impact: str
    complexity_level: FeatureComplexity
    estimated_setup_time: int  # minutes

class IntentClassifier:
    """Classifies user intents from natural language input"""
    
    def __init__(self):
        self.intent_patterns = {
            IntentType.SETUP_NEW_SYSTEM: [
                r"i want to.*use.*for",
                r"help.*set.*up",
                r"configure.*new",
                r"getting started",
                r"how do i.*setup",
                r"install.*configure",
                r"first time"
            ],
            IntentType.OPTIMIZE_EXISTING: [
                r"improve.*performance",
                r"optimize.*system",
                r"make.*faster",
                r"better.*settings",
                r"speed up",
                r"enhance.*experience"
            ],
            IntentType.TROUBLESHOOT_ISSUE: [
                r"not working",
                r"problem.*with",
                r"error.*occurred",
                r"something.*wrong",
                r"fix.*issue",
                r"troubleshoot",
                r"broken"
            ],
            IntentType.LEARN_FEATURES: [
                r"what.*can.*do",
                r"show.*features",
                r"how.*works",
                r"explain.*functionality",
                r"learn.*about",
                r"capabilities"
            ],
            IntentType.COMPARE_OPTIONS: [
                r"compare.*options",
                r"difference.*between",
                r"which.*better",
                r"pros.*cons",
                r"versus",
                r"choose.*between"
            ],
            IntentType.GET_RECOMMENDATIONS: [
                r"recommend.*settings",
                r"best.*configuration",
                r"suggest.*setup",
                r"what.*should.*use",
                r"advice.*on",
                r"optimal.*for"
            ],
            IntentType.UNDERSTAND_HARDWARE: [
                r"my.*hardware",
                r"system.*requirements",
                r"compatible.*with",
                r"will.*work.*with",
                r"hardware.*support",
                r"device.*capability"
            ],
            IntentType.COST_ANALYSIS: [
                r"cost.*of",
                r"price.*for",
                r"expensive.*to",
                r"budget.*for",
                r"affordable.*option",
                r"cheap.*alternative"
            ]
        }
        
        self.context_keywords = {
            "urgency": ["urgent", "quickly", "asap", "immediately", "rush"],
            "complexity": ["simple", "easy", "advanced", "complex", "detailed"],
            "experience": ["beginner", "new", "expert", "experienced", "professional"]
        }
    
    def classify_intent(self, user_input: str, conversation_history: List[str] = None) -> UserIntent:
        """Classify user intent from natural language input"""
        user_input_lower = user_input.lower()
        
        # Score each intent type
        intent_scores = {}
        for intent_type, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, user_input_lower):
                    score += 1
            intent_scores[intent_type] = score / len(patterns)
        
        # Find highest scoring intent
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        
        if best_intent[1] == 0:
            # No clear intent, default to setup
            intent_type = IntentType.SETUP_NEW_SYSTEM
            confidence = 0.3
        else:
            intent_type = best_intent[0]
            confidence = min(best_intent[1] * 2, 1.0)  # Scale confidence
        
        # Extract parameters
        parameters = self._extract_parameters(user_input_lower)
        
        # Add context from conversation history
        context = self._analyze_context(user_input_lower, conversation_history)
        
        return UserIntent(intent_type, confidence, parameters, context)
    
    def _extract_parameters(self, user_input: str) -> Dict[str, Any]:
        """Extract specific parameters from user input"""
        parameters = {}
        
        # Extract use case mentions
        use_cases = []
        use_case_patterns = [
            r"for\s+([^,.!?]+)",
            r"to\s+([^,.!?]+)",
            r"use.*for\s+([^,.!?]+)"
        ]
        
        for pattern in use_case_patterns:
            matches = re.findall(pattern, user_input)
            use_cases.extend(matches)
        
        if use_cases:
            parameters["use_cases"] = [uc.strip() for uc in use_cases[:3]]
        
        # Extract hardware mentions
        hardware_keywords = ["laptop", "desktop", "mobile", "tablet", "phone", "computer"]
        mentioned_hardware = [hw for hw in hardware_keywords if hw in user_input]
        if mentioned_hardware:
            parameters["hardware_type"] = mentioned_hardware[0]
        
        # Extract experience level
        for level, keywords in [
            ("beginner", ["beginner", "new", "first time", "never used"]),
            ("intermediate", ["some experience", "used before", "familiar"]),
            ("expert", ["expert", "professional", "advanced", "experienced"])
        ]:
            if any(keyword in user_input for keyword in keywords):
                parameters["experience_level"] = level
                break
        
        return parameters
    
    def _analyze_context(self, user_input: str, conversation_history: List[str] = None) -> Optional[str]:
        """Analyze conversation context"""
        context_indicators = []
        
        for context_type, keywords in self.context_keywords.items():
            if any(keyword in user_input for keyword in keywords):
                context_indicators.append(context_type)
        
        return ";".join(context_indicators) if context_indicators else None

class RequirementGatherer:
    """Gathers user requirements through targeted questions"""
    
    def __init__(self):
        self.question_templates = {
            "primary_use_case": [
                "What do you primarily want to use this system for?",
                "What's your main goal with this setup?",
                "How do you plan to use this most often?"
            ],
            "experience_level": [
                "How would you describe your technical experience level?",
                "Are you new to this type of system or have you used similar tools before?",
                "Would you prefer a simple setup or are you comfortable with advanced options?"
            ],
            "performance_priority": [
                "What's more important to you: maximum performance or ease of use?",
                "Are you willing to sacrifice some simplicity for better performance?",
                "Do you prioritize speed, reliability, or user-friendliness?"
            ],
            "hardware_constraints": [
                "Are there any limitations with your current hardware I should know about?",
                "What device will you primarily be using this on?",
                "Do you have any specific hardware requirements or constraints?"
            ],
            "budget_considerations": [
                "Do you have any budget constraints for additional software or services?",
                "Are you looking for free options or open to premium features?",
                "What's your budget range for this setup?"
            ],
            "timeline": [
                "When do you need this system to be up and running?",
                "Is this urgent or can we take time to get it right?",
                "How much time can you dedicate to the initial setup?"
            ]
        }
        
        self.follow_up_questions = {
            "clarify_use_case": [
                "Can you tell me more about that specific use case?",
                "What features would be most important for that purpose?",
                "Are there any specific requirements for that type of work?"
            ],
            "technical_comfort": [
                "Are you comfortable editing configuration files?",
                "Do you prefer graphical interfaces or are you okay with command-line tools?",
                "How do you usually prefer to learn new software?"
            ]
        }
    
    def get_next_question(self, context: ConversationContext, 
                         requirement_type: str) -> Optional[str]:
        """Get the next appropriate question based on context"""
        if requirement_type not in self.question_templates:
            return None
        
        questions = self.question_templates[requirement_type]
        
        # Select question based on user's apparent expertise
        if context.gathered_requirements.get("experience_level") == "expert":
            # Use more technical questions for experts
            return questions[-1] if len(questions) > 1 else questions[0]
        else:
            # Use simpler questions for beginners
            return questions[0]
    
    def analyze_response(self, response: str, question_type: str) -> Dict[str, Any]:
        """Analyze user response to extract requirements"""
        response_lower = response.lower()
        analysis = {}
        
        if question_type == "primary_use_case":
            # Extract use case keywords
            use_case_mapping = {
                "business": ["business", "work", "professional", "enterprise"],
                "personal": ["personal", "home", "family", "myself"],
                "education": ["learn", "study", "school", "research", "education"],
                "creative": ["creative", "design", "art", "content", "media"],
                "development": ["develop", "code", "programming", "software"]
            }
            
            for category, keywords in use_case_mapping.items():
                if any(keyword in response_lower for keyword in keywords):
                    analysis["primary_category"] = category
                    break
            
            # Extract specific activities
            activity_keywords = re.findall(r'\b\w+ing\b', response_lower)  # Words ending in -ing
            if activity_keywords:
                analysis["activities"] = activity_keywords[:3]
        
        elif question_type == "experience_level":
            level_indicators = {
                "beginner": ["new", "beginner", "first time", "never", "don't know"],
                "intermediate": ["some", "little", "basic", "used before"],
                "expert": ["expert", "experienced", "professional", "advanced", "years"]
            }
            
            for level, indicators in level_indicators.items():
                if any(indicator in response_lower for indicator in indicators):
                    analysis["experience_level"] = level
                    break
        
        elif question_type == "performance_priority":
            priority_mapping = {
                "performance": ["performance", "speed", "fast", "efficient"],
                "usability": ["easy", "simple", "user-friendly", "intuitive"],
                "reliability": ["reliable", "stable", "consistent", "dependable"],
                "features": ["features", "functionality", "capabilities", "options"]
            }
            
            priorities = []
            for priority, keywords in priority_mapping.items():
                if any(keyword in response_lower for keyword in keywords):
                    priorities.append(priority)
            
            analysis["priorities"] = priorities[:2]  # Top 2 priorities
        
        return analysis

class ConfigurationRecommender:
    """Provides intelligent configuration recommendations"""
    
    def __init__(self):
        self.configuration_templates = self._initialize_templates()
        self.hardware_requirements = self._initialize_hardware_requirements()
    
    def _initialize_templates(self) -> Dict[str, ConfigurationTemplate]:
        """Initialize configuration templates for common scenarios"""
        return {
            "beginner_general": ConfigurationTemplate(
                "beginner_general",
                "Simple General Use",
                "Perfect for new users who want a straightforward setup",
                ["basic document editing", "web browsing", "light productivity"],
                {"ram_gb": 4, "storage_gb": 10, "cpu_cores": 2},
                {
                    "interface_complexity": "minimal",
                    "auto_updates": True,
                    "safety_features": "maximum",
                    "help_tooltips": "enabled"
                },
                "Low resource usage, fast startup",
                FeatureComplexity.ESSENTIAL,
                15
            ),
            "professional_productivity": ConfigurationTemplate(
                "professional_productivity",
                "Professional Productivity",
                "Optimized for business users who need efficiency",
                ["business workflows", "team collaboration", "document management"],
                {"ram_gb": 8, "storage_gb": 25, "cpu_cores": 4},
                {
                    "interface_complexity": "intermediate",
                    "keyboard_shortcuts": "enabled",
                    "advanced_features": "contextual",
                    "integration_apis": "enabled"
                },
                "Balanced performance and features",
                FeatureComplexity.INTERMEDIATE,
                30
            ),
            "developer_advanced": ConfigurationTemplate(
                "developer_advanced",
                "Developer Advanced",
                "Full-featured setup for technical users",
                ["software development", "system administration", "advanced customization"],
                {"ram_gb": 16, "storage_gb": 50, "cpu_cores": 8},
                {
                    "interface_complexity": "full",
                    "debug_tools": "enabled",
                    "api_access": "full",
                    "customization": "maximum"
                },
                "High performance, all features available",
                FeatureComplexity.EXPERT,
                60
            ),
            "mobile_optimized": ConfigurationTemplate(
                "mobile_optimized",
                "Mobile Optimized",
                "Designed for touch devices and mobile use",
                ["mobile productivity", "on-the-go access", "touch interface"],
                {"screen_size": "small", "touch": True, "battery_conscious": True},
                {
                    "touch_friendly": True,
                    "gesture_controls": "enabled",
                    "battery_optimization": "aggressive",
                    "offline_mode": "enabled"
                },
                "Optimized for mobile devices",
                FeatureComplexity.BASIC,
                20
            )
        }
    
    def _initialize_hardware_requirements(self) -> Dict[str, Dict[str, Any]]:
        """Initialize hardware requirement mappings"""
        return {
            "minimal": {"ram_gb": 2, "storage_gb": 5, "cpu_score": 100},
            "recommended": {"ram_gb": 8, "storage_gb": 20, "cpu_score": 500},
            "optimal": {"ram_gb": 16, "storage_gb": 50, "cpu_score": 1000}
        }
    
    def recommend_configurations(self, requirements: Dict[str, Any], 
                               hardware_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate configuration recommendations based on requirements and hardware"""
        recommendations = []
        
        # Score each template based on requirements
        for template_id, template in self.configuration_templates.items():
            score = self._score_template(template, requirements, hardware_info)
            if score > 0.3:  # Only include viable options
                recommendations.append({
                    "template": template,
                    "score": score,
                    "compatibility": self._check_hardware_compatibility(template, hardware_info),
                    "customizations": self._suggest_customizations(template, requirements)
                })
        
        # Sort by score and return top recommendations
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:3]
    
    def _score_template(self, template: ConfigurationTemplate, 
                       requirements: Dict[str, Any], 
                       hardware_info: Dict[str, Any]) -> float:
        """Score how well a template matches requirements"""
        score = 0.0
        
        # Experience level matching
        req_experience = requirements.get("experience_level", "beginner")
        template_complexity = template.complexity_level
        
        experience_complexity_map = {
            "beginner": [FeatureComplexity.ESSENTIAL, FeatureComplexity.BASIC],
            "intermediate": [FeatureComplexity.BASIC, FeatureComplexity.INTERMEDIATE],
            "expert": [FeatureComplexity.INTERMEDIATE, FeatureComplexity.ADVANCED, FeatureComplexity.EXPERT]
        }
        
        if template_complexity in experience_complexity_map.get(req_experience, []):
            score += 0.4
        
        # Use case matching
        req_use_cases = requirements.get("use_cases", [])
        for use_case in req_use_cases:
            for template_use_case in template.use_cases:
                if any(word in template_use_case.lower() for word in use_case.lower().split()):
                    score += 0.2
                    break
        
        # Hardware compatibility
        compatibility = self._check_hardware_compatibility(template, hardware_info)
        if compatibility["meets_requirements"]:
            score += 0.3
        else:
            score -= 0.2
        
        # Priority matching
        priorities = requirements.get("priorities", [])
        if "performance" in priorities and template_complexity in [FeatureComplexity.ADVANCED, FeatureComplexity.EXPERT]:
            score += 0.1
        if "usability" in priorities and template_complexity in [FeatureComplexity.ESSENTIAL, FeatureComplexity.BASIC]:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _check_hardware_compatibility(self, template: ConfigurationTemplate, 
                                    hardware_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check if hardware meets template requirements"""
        compatibility = {
            "meets_requirements": True,
            "warnings": [],
            "limitations": []
        }
        
        # Check RAM
        required_ram = template.required_hardware.get("ram_gb", 0)
        available_ram = hardware_info.get("ram_gb", 0)
        
        if available_ram < required_ram:
            compatibility["meets_requirements"] = False
            compatibility["warnings"].append(
                f"Requires {required_ram}GB RAM, but only {available_ram}GB available"
            )
        
        # Check storage
        required_storage = template.required_hardware.get("storage_gb", 0)
        available_storage = hardware_info.get("available_storage_gb", float('inf'))
        
        if available_storage < required_storage:
            compatibility["warnings"].append(
                f"May require {required_storage}GB storage space"
            )
        
        # Check CPU
        required_cores = template.required_hardware.get("cpu_cores", 1)
        available_cores = hardware_info.get("cpu_cores", 1)
        
        if available_cores < required_cores:
            compatibility["limitations"].append(
                f"Performance may be limited with {available_cores} CPU cores (recommended: {required_cores})"
            )
        
        return compatibility
    
    def _suggest_customizations(self, template: ConfigurationTemplate, 
                              requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest customizations to the base template"""
        customizations = {}
        
        # Adjust based on priorities
        priorities = requirements.get("priorities", [])
        
        if "performance" in priorities:
            customizations.update({
                "cache_size": "large",
                "background_processes": "minimal",
                "optimization_level": "aggressive"
            })
        
        if "usability" in priorities:
            customizations.update({
                "tutorial_mode": "extended",
                "help_system": "comprehensive",
                "error_recovery": "automatic"
            })
        
        # Adjust for hardware constraints
        if requirements.get("hardware_type") == "mobile":
            customizations.update({
                "touch_optimization": True,
                "battery_saving": True,
                "data_compression": True
            })
        
        return customizations

class ChatbotConfigurationAssistant:
    """
    Main chatbot assistant for system configuration
    
    Provides natural language interface for complex system setup with
    intelligent recommendations, explanations, and step-by-step guidance.
    """
    
    def __init__(self, interface_intelligence: InterfaceIntelligence,
                 disclosure_engine: ProgressiveDisclosureEngine):
        self.interface_intelligence = interface_intelligence
        self.disclosure_engine = disclosure_engine
        self.intent_classifier = IntentClassifier()
        self.requirement_gatherer = RequirementGatherer()
        self.recommender = ConfigurationRecommender()
        
        self.active_conversations: Dict[str, ConversationContext] = {}
        self.logger = logging.getLogger(__name__)
    
    async def start_conversation(self, user_id: str, initial_message: str) -> AssistantResponse:
        """Start a new configuration conversation"""
        session_id = f"{user_id}_{datetime.utcnow().isoformat()}"
        
        # Classify initial intent
        intent = self.intent_classifier.classify_intent(initial_message)
        
        # Create conversation context
        context = ConversationContext(
            user_id=user_id,
            session_id=session_id,
            state=ConversationState.INTENT_DISCOVERY,
            intent=intent
        )
        
        self.active_conversations[session_id] = context
        
        # Generate welcome response
        response = await self._generate_welcome_response(context, initial_message)
        
        return response
    
    async def continue_conversation(self, session_id: str, user_message: str) -> AssistantResponse:
        """Continue an existing conversation"""
        if session_id not in self.active_conversations:
            return AssistantResponse(
                ResponseType.WARNING,
                "I'm sorry, I couldn't find our conversation. Let's start fresh!"
            )
        
        context = self.active_conversations[session_id]
        
        # Process user response based on current state
        if context.state == ConversationState.INTENT_DISCOVERY:
            return await self._handle_intent_discovery(context, user_message)
        elif context.state == ConversationState.REQUIREMENT_GATHERING:
            return await self._handle_requirement_gathering(context, user_message)
        elif context.state == ConversationState.HARDWARE_ANALYSIS:
            return await self._handle_hardware_analysis(context, user_message)
        elif context.state == ConversationState.OPTION_PRESENTATION:
            return await self._handle_option_selection(context, user_message)
        elif context.state == ConversationState.CONFIGURATION:
            return await self._handle_configuration(context, user_message)
        elif context.state == ConversationState.VALIDATION:
            return await self._handle_validation(context, user_message)
        else:
            return await self._handle_general_response(context, user_message)
    
    async def _generate_welcome_response(self, context: ConversationContext, 
                                       initial_message: str) -> AssistantResponse:
        """Generate appropriate welcome response based on detected intent"""
        intent = context.intent
        
        if intent.confidence > 0.7:
            # High confidence intent, provide targeted response
            if intent.intent_type == IntentType.SETUP_NEW_SYSTEM:
                message = ("Great! I'll help you set up your system. "
                          "To give you the best recommendations, I'd like to understand "
                          "your specific needs and current hardware setup.")
                next_question = "What do you primarily want to use this system for?"
                
            elif intent.intent_type == IntentType.TROUBLESHOOT_ISSUE:
                message = ("I'm here to help troubleshoot your issue. "
                          "Let me gather some information to provide the best solution.")
                next_question = "Can you describe the specific problem you're experiencing?"
                
            elif intent.intent_type == IntentType.LEARN_FEATURES:
                message = ("I'd be happy to explain the features and capabilities! "
                          "Let me tailor my explanation to your experience level.")
                next_question = "How familiar are you with this type of system?"
                
            else:
                message = ("I understand you're looking for help with configuration. "
                          "Let me ask a few questions to provide the most relevant assistance.")
                next_question = "What's your main goal with this setup?"
        else:
            # Low confidence, ask clarifying question
            message = ("Hello! I'm here to help you configure your system. "
                      "I can assist with setup, troubleshooting, feature explanations, and recommendations.")
            next_question = "What would you like help with today?"
        
        context.state = ConversationState.REQUIREMENT_GATHERING
        context.current_question = next_question
        
        return AssistantResponse(
            ResponseType.QUESTION,
            message,
            next_question=next_question
        )
    
    async def _handle_intent_discovery(self, context: ConversationContext, 
                                     user_message: str) -> AssistantResponse:
        """Handle intent discovery phase"""
        # Re-classify intent with more context
        intent = self.intent_classifier.classify_intent(user_message)
        context.intent = intent
        context.state = ConversationState.REQUIREMENT_GATHERING
        
        return await self._handle_requirement_gathering(context, user_message)
    
    async def _handle_requirement_gathering(self, context: ConversationContext, 
                                          user_message: str) -> AssistantResponse:
        """Handle requirement gathering phase"""
        # Analyze the response if we were asking a specific question
        if context.current_question:
            question_type = self._identify_question_type(context.current_question)
            analysis = self.requirement_gatherer.analyze_response(user_message, question_type)
            context.gathered_requirements.update(analysis)
        
        # Determine what requirement to gather next
        missing_requirements = self._identify_missing_requirements(context.gathered_requirements)
        
        if missing_requirements:
            requirement_type = missing_requirements[0]
            next_question = self.requirement_gatherer.get_next_question(context, requirement_type)
            
            context.current_question = next_question
            context.question_attempts += 1
            
            return AssistantResponse(
                ResponseType.QUESTION,
                f"Thanks for that information! {next_question}",
                next_question=next_question
            )
        else:
            # All requirements gathered, move to hardware analysis
            context.state = ConversationState.HARDWARE_ANALYSIS
            return await self._transition_to_hardware_analysis(context)
    
    def _identify_question_type(self, question: str) -> str:
        """Identify the type of question being asked"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["use", "goal", "purpose"]):
            return "primary_use_case"
        elif any(word in question_lower for word in ["experience", "technical", "comfort"]):
            return "experience_level"
        elif any(word in question_lower for word in ["performance", "priority", "important"]):
            return "performance_priority"
        elif any(word in question_lower for word in ["hardware", "device", "system"]):
            return "hardware_constraints"
        elif any(word in question_lower for word in ["budget", "cost", "price"]):
            return "budget_considerations"
        elif any(word in question_lower for word in ["time", "when", "deadline"]):
            return "timeline"
        else:
            return "general"
    
    def _identify_missing_requirements(self, requirements: Dict[str, Any]) -> List[str]:
        """Identify which requirements are still missing"""
        essential_requirements = [
            "primary_use_case",
            "experience_level",
            "performance_priority"
        ]
        
        missing = []
        for req in essential_requirements:
            if req not in requirements or not requirements[req]:
                missing.append(req)
        
        return missing
    
    async def _transition_to_hardware_analysis(self, context: ConversationContext) -> AssistantResponse:
        """Transition to hardware analysis phase"""
        message = ("Perfect! Now let me analyze your hardware to ensure we choose "
                  "the best configuration for your system.")
        
        # Get hardware information
        user_profile = await self.interface_intelligence.get_user_profile(context.user_id)
        if user_profile and hasattr(user_profile, 'device_info'):
            context.hardware_info = user_profile.device_info
            return await self._proceed_to_recommendations(context)
        else:
            context.state = ConversationState.HARDWARE_ANALYSIS
            return AssistantResponse(
                ResponseType.QUESTION,
                message + " Can you tell me about your device? (e.g., 'MacBook Pro', 'Windows desktop', 'Android tablet')",
                next_question="What type of device are you using?"
            )
    
    async def _handle_hardware_analysis(self, context: ConversationContext, 
                                      user_message: str) -> AssistantResponse:
        """Handle hardware analysis phase"""
        # Parse hardware information from user message
        hardware_info = self._parse_hardware_info(user_message)
        context.hardware_info = hardware_info
        
        return await self._proceed_to_recommendations(context)
    
    def _parse_hardware_info(self, hardware_description: str) -> Dict[str, Any]:
        """Parse hardware information from user description"""
        hardware_info = {
            "device_type": "unknown",
            "ram_gb": 8,  # Default assumption
            "cpu_cores": 4,  # Default assumption
            "available_storage_gb": 100  # Default assumption
        }
        
        description_lower = hardware_description.lower()
        
        # Device type detection
        if any(word in description_lower for word in ["laptop", "macbook", "notebook"]):
            hardware_info["device_type"] = "laptop"
        elif any(word in description_lower for word in ["desktop", "pc", "workstation"]):
            hardware_info["device_type"] = "desktop"
        elif any(word in description_lower for word in ["phone", "mobile", "android", "iphone"]):
            hardware_info["device_type"] = "mobile"
        elif any(word in description_lower for word in ["tablet", "ipad"]):
            hardware_info["device_type"] = "tablet"
        
        # RAM detection
        ram_match = re.search(r'(\d+)\s*gb.*ram', description_lower)
        if ram_match:
            hardware_info["ram_gb"] = int(ram_match.group(1))
        
        # CPU detection
        if any(word in description_lower for word in ["i7", "i9", "powerful", "high-end"]):
            hardware_info["cpu_cores"] = 8
        elif any(word in description_lower for word in ["i5", "medium", "mid-range"]):
            hardware_info["cpu_cores"] = 4
        elif any(word in description_lower for word in ["i3", "basic", "entry"]):
            hardware_info["cpu_cores"] = 2
        
        return hardware_info
    
    async def _proceed_to_recommendations(self, context: ConversationContext) -> AssistantResponse:
        """Generate and present configuration recommendations"""
        context.state = ConversationState.OPTION_PRESENTATION
        
        # Generate recommendations
        recommendations = self.recommender.recommend_configurations(
            context.gathered_requirements,
            context.hardware_info
        )
        
        if not recommendations:
            return AssistantResponse(
                ResponseType.WARNING,
                "I'm having trouble finding suitable configurations for your requirements. "
                "Let me ask a few more specific questions to help narrow things down.",
                next_question="What's the most important aspect: ease of use, performance, or features?"
            )
        
        # Format recommendations for presentation
        message = "Based on your requirements and hardware, I've found some great options for you:\n\n"
        options = []
        
        for i, rec in enumerate(recommendations, 1):
            template = rec["template"]
            compatibility = rec["compatibility"]
            
            option_text = f"**{i}. {template.name}**\n"
            option_text += f"   {template.description}\n"
            option_text += f"   Setup time: ~{template.estimated_setup_time} minutes\n"
            option_text += f"   {template.performance_impact}\n"
            
            if not compatibility["meets_requirements"]:
                option_text += f"   ⚠️  Some limitations with your hardware\n"
            
            options.append({
                "id": i,
                "template_id": template.template_id,
                "name": template.name,
                "description": template.description,
                "recommendation_data": rec
            })
            
            message += option_text + "\n"
        
        message += "Which option interests you most? I can explain any of these in more detail."
        
        return AssistantResponse(
            ResponseType.RECOMMENDATION,
            message,
            options=options,
            next_question="Which configuration would you like to learn more about?"
        )
    
    async def _handle_option_selection(self, context: ConversationContext, 
                                     user_message: str) -> AssistantResponse:
        """Handle user's option selection"""
        # Parse selection
        selection = self._parse_selection(user_message)
        
        if selection is None:
            return AssistantResponse(
                ResponseType.QUESTION,
                "I didn't catch which option you'd like to explore. "
                "Could you tell me the number (1, 2, 3) or name of the configuration?",
                next_question="Which configuration interests you?"
            )
        
        # Generate detailed explanation and proceed to configuration
        context.state = ConversationState.CONFIGURATION
        return await self._explain_and_configure(context, selection)
    
    def _parse_selection(self, user_message: str) -> Optional[int]:
        """Parse user's selection from their message"""
        # Look for numbers
        numbers = re.findall(r'\b(\d+)\b', user_message)
        if numbers:
            try:
                selection = int(numbers[0])
                if 1 <= selection <= 3:
                    return selection
            except ValueError:
                pass
        
        # Look for keywords like "first", "second", etc.
        ordinals = {
            "first": 1, "second": 2, "third": 3,
            "1st": 1, "2nd": 2, "3rd": 3
        }
        
        user_message_lower = user_message.lower()
        for ordinal, number in ordinals.items():
            if ordinal in user_message_lower:
                return number
        
        return None
    
    async def _explain_and_configure(self, context: ConversationContext, 
                                   selection: int) -> AssistantResponse:
        """Explain selected configuration and start setup"""
        # This would contain the detailed configuration logic
        message = f"Excellent choice! Let me walk you through setting up option {selection}.\n\n"
        message += "I'll guide you through each step and explain what we're doing along the way. "
        message += "You can ask questions at any time, and if something doesn't work, "
        message += "we can always adjust the configuration.\n\n"
        message += "Ready to begin the setup?"
        
        return AssistantResponse(
            ResponseType.CONFIRMATION,
            message,
            requires_confirmation=True,
            next_question="Shall we start the configuration process?"
        )
    
    async def _handle_configuration(self, context: ConversationContext, 
                                  user_message: str) -> AssistantResponse:
        """Handle the configuration phase"""
        if self._is_affirmative(user_message):
            context.state = ConversationState.COMPLETION
            return AssistantResponse(
                ResponseType.INSTRUCTION,
                "Perfect! Here's your step-by-step configuration guide:\n\n"
                "1. First, we'll optimize your interface settings...\n"
                "2. Then configure the essential features...\n"
                "3. Finally, test everything works correctly.\n\n"
                "I'll be here to help if you run into any issues!",
                configuration_data={"steps": ["interface", "features", "testing"]}
            )
        else:
            return AssistantResponse(
                ResponseType.QUESTION,
                "No problem! Is there anything you'd like to modify about the configuration, "
                "or would you prefer to see different options?",
                next_question="How would you like to proceed?"
            )
    
    async def _handle_validation(self, context: ConversationContext, 
                                user_message: str) -> AssistantResponse:
        """Handle configuration validation"""
        # Implementation for validating the configuration
        return AssistantResponse(
            ResponseType.CELEBRATION,
            "🎉 Congratulations! Your system is now configured and ready to use. "
            "I've set up everything according to your preferences, and you can always "
            "come back to adjust settings as you become more familiar with the system."
        )
    
    async def _handle_general_response(self, context: ConversationContext, 
                                     user_message: str) -> AssistantResponse:
        """Handle general responses and questions"""
        # Handle general questions and provide helpful responses
        if any(word in user_message.lower() for word in ["help", "explain", "what", "how"]):
            return AssistantResponse(
                ResponseType.EXPLANATION,
                "I'm here to help with any questions! You can ask me about:\n"
                "• Configuration options and their trade-offs\n"
                "• Hardware compatibility and requirements\n"
                "• Step-by-step setup instructions\n"
                "• Troubleshooting issues\n"
                "• Feature explanations\n\n"
                "What would you like to know more about?"
            )
        
        return AssistantResponse(
            ResponseType.QUESTION,
            "I'm not sure I understood that completely. "
            "Could you rephrase your question or let me know how I can help?",
            next_question="What would you like assistance with?"
        )
    
    def _is_affirmative(self, message: str) -> bool:
        """Check if message indicates agreement"""
        affirmative_words = ["yes", "yeah", "yep", "sure", "okay", "ok", "go ahead", "let's do it"]
        return any(word in message.lower() for word in affirmative_words)
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of conversation for analytics"""
        if session_id not in self.active_conversations:
            return {}
        
        context = self.active_conversations[session_id]
        
        return {
            "session_id": session_id,
            "user_id": context.user_id,
            "state": context.state.value,
            "intent": context.intent.intent_type.value if context.intent else None,
            "requirements_gathered": len(context.gathered_requirements),
            "question_attempts": context.question_attempts,
            "hardware_analyzed": bool(context.hardware_info),
            "completion_status": "completed" if context.state == ConversationState.COMPLETION else "in_progress"
        }