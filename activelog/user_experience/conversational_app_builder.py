"""
Conversational App Builder System
Natural language interface for building applications through conversation
"""

import asyncio
import time
import logging
import json
import uuid
import re
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel, pipeline
import numpy as np

class ConversationState(Enum):
    INITIAL_CONCEPT = "initial_concept"
    FEATURE_DISCOVERY = "feature_discovery"
    COMPONENT_SELECTION = "component_selection"
    DESIGN_PREFERENCES = "design_preferences"
    CONFIGURATION = "configuration"
    REVIEW_AND_REFINE = "review_and_refine"
    DEPLOYMENT_PLANNING = "deployment_planning"
    COMPLETED = "completed"

class ResponseStyle(Enum):
    BEGINNER_FRIENDLY = "beginner_friendly"
    TECHNICAL = "technical"
    ENCOURAGING = "encouraging"
    CONCISE = "concise"
    DETAILED = "detailed"

class QuestionType(Enum):
    OPEN_ENDED = "open_ended"
    YES_NO = "yes_no"
    MULTIPLE_CHOICE = "multiple_choice"
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"

@dataclass
class ConversationContext:
    session_id: str
    user_id: str
    current_state: ConversationState
    app_concept: str
    discovered_features: List[str]
    selected_components: List[Dict[str, Any]]
    design_preferences: Dict[str, Any]
    technical_requirements: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]
    confidence_scores: Dict[str, float]
    pending_clarifications: List[str]

@dataclass
class ConversationResponse:
    message: str
    response_type: str
    suggestions: List[str]
    questions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    next_state: Optional[ConversationState]
    confidence: float
    visual_aids: List[Dict[str, Any]] = field(default_factory=list)

class ConversationalAI(nn.Module):
    """Advanced conversational AI for app building guidance"""
    
    def __init__(self, vocab_size: int = 30000):
        super().__init__()
        
        # Context understanding
        self.context_encoder = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(
                d_model=768,
                nhead=12,
                dim_feedforward=2048,
                dropout=0.1
            ),
            num_layers=6
        )
        
        # Intent classification
        self.intent_classifier = nn.Sequential(
            nn.Linear(768, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 20)  # 20 different intents
        )
        
        # Response generation strategy
        self.response_strategy = nn.Sequential(
            nn.Linear(768 + 256, 512),  # Context + intent
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, len(ResponseStyle))
        )
        
        # Confidence estimator
        self.confidence_estimator = nn.Sequential(
            nn.Linear(768, 256),
            nn.ReLU(),
            nn.Linear(256, 1),
            nn.Sigmoid()
        )
        
        # Question generator
        self.question_type_predictor = nn.Sequential(
            nn.Linear(768, 256),
            nn.ReLU(),
            nn.Linear(256, len(QuestionType))
        )

class ConversationalAppBuilder:
    """Main conversational app building system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # AI models
        self.conversational_ai = ConversationalAI()
        self.tokenizer = AutoTokenizer.from_pretrained('microsoft/DialoGPT-medium')
        
        # Conversation management
        self.active_conversations = {}
        
        # Response templates
        self.response_templates = self._initialize_response_templates()
        
        # Question patterns
        self.question_patterns = self._initialize_question_patterns()
        
        # Component knowledge base
        self.component_knowledge = self._initialize_component_knowledge()
        
        # Feature discovery engine
        self.feature_discovery = FeatureDiscoveryEngine()
        
        # Explanation generator
        self.explanation_generator = ExplanationGenerator()
        
        self.logger.info("Conversational App Builder initialized")
    
    async def start_conversation(self, user_id: str, initial_message: str = None) -> Dict[str, Any]:
        """Start a new conversational app building session"""
        
        self.logger.info(f"Starting conversation for user: {user_id}")
        
        try:
            session_id = str(uuid.uuid4())
            
            # Create conversation context
            context = ConversationContext(
                session_id=session_id,
                user_id=user_id,
                current_state=ConversationState.INITIAL_CONCEPT,
                app_concept="",
                discovered_features=[],
                selected_components=[],
                design_preferences={},
                technical_requirements={},
                conversation_history=[],
                user_preferences={},
                confidence_scores={},
                pending_clarifications=[]
            )
            
            self.active_conversations[session_id] = context
            
            # Generate initial response
            if initial_message:
                # User provided initial concept
                response = await self._process_message(session_id, initial_message)
            else:
                # Start with welcome message
                response = await self._generate_welcome_response(context)
            
            return {
                'session_id': session_id,
                'response': response,
                'conversation_state': context.current_state.value,
                'progress': self._calculate_progress(context)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start conversation: {e}")
            return {'error': str(e)}
    
    async def continue_conversation(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """Continue an existing conversation"""
        
        if session_id not in self.active_conversations:
            return {'error': 'Conversation session not found'}
        
        try:
            response = await self._process_message(session_id, user_message)
            context = self.active_conversations[session_id]
            
            return {
                'response': response,
                'conversation_state': context.current_state.value,
                'progress': self._calculate_progress(context),
                'app_preview': self._generate_app_preview(context) if response.next_state else None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process message: {e}")
            return {'error': str(e)}
    
    async def _process_message(self, session_id: str, user_message: str) -> ConversationResponse:
        """Process user message and generate appropriate response"""
        
        context = self.active_conversations[session_id]
        
        # Add message to history
        context.conversation_history.append({
            'timestamp': time.time(),
            'type': 'user',
            'message': user_message
        })
        
        # Analyze message intent and extract information
        analysis = await self._analyze_user_message(user_message, context)
        
        # Update context based on analysis
        await self._update_context_from_analysis(context, analysis)
        
        # Generate response based on current state
        response = await self._generate_response(context, analysis)
        
        # Update conversation state if needed
        if response.next_state:
            context.current_state = response.next_state
        
        # Add response to history
        context.conversation_history.append({
            'timestamp': time.time(),
            'type': 'assistant',
            'message': response.message,
            'suggestions': response.suggestions,
            'actions': response.actions
        })
        
        return response
    
    async def _analyze_user_message(self, message: str, context: ConversationContext) -> Dict[str, Any]:
        """Analyze user message to extract intent and information"""
        
        analysis = {
            'intent': 'unknown',
            'confidence': 0.5,
            'extracted_features': [],
            'mentioned_components': [],
            'design_preferences': {},
            'technical_details': {},
            'questions': [],
            'affirmations': [],
            'negations': []
        }
        
        message_lower = message.lower()
        
        # Intent detection
        if any(word in message_lower for word in ['yes', 'yeah', 'sure', 'ok', 'sounds good']):
            analysis['intent'] = 'affirmation'
            analysis['confidence'] = 0.9
            
        elif any(word in message_lower for word in ['no', 'nah', 'not really', 'don\'t think so']):
            analysis['intent'] = 'negation'
            analysis['confidence'] = 0.9
            
        elif any(word in message_lower for word in ['help', 'explain', 'what is', 'how does']):
            analysis['intent'] = 'request_explanation'
            analysis['confidence'] = 0.8
            
        elif any(word in message_lower for word in ['want', 'need', 'would like', 'looking for']):
            analysis['intent'] = 'express_requirement'
            analysis['confidence'] = 0.8
            
        elif any(word in message_lower for word in ['change', 'modify', 'different', 'instead']):
            analysis['intent'] = 'request_modification'
            analysis['confidence'] = 0.7
        
        # Feature extraction
        features = self._extract_features_from_text(message)
        analysis['extracted_features'] = features
        
        # Component mentions
        components = self._extract_component_mentions(message)
        analysis['mentioned_components'] = components
        
        # Design preferences
        design_prefs = self._extract_design_preferences(message)
        analysis['design_preferences'] = design_prefs
        
        # Technical details
        tech_details = self._extract_technical_details(message)
        analysis['technical_details'] = tech_details
        
        return analysis
    
    async def _generate_response(self, context: ConversationContext, 
                               analysis: Dict[str, Any]) -> ConversationResponse:
        """Generate appropriate response based on context and analysis"""
        
        state = context.current_state
        
        if state == ConversationState.INITIAL_CONCEPT:
            return await self._handle_initial_concept(context, analysis)
        elif state == ConversationState.FEATURE_DISCOVERY:
            return await self._handle_feature_discovery(context, analysis)
        elif state == ConversationState.COMPONENT_SELECTION:
            return await self._handle_component_selection(context, analysis)
        elif state == ConversationState.DESIGN_PREFERENCES:
            return await self._handle_design_preferences(context, analysis)
        elif state == ConversationState.CONFIGURATION:
            return await self._handle_configuration(context, analysis)
        elif state == ConversationState.REVIEW_AND_REFINE:
            return await self._handle_review_and_refine(context, analysis)
        elif state == ConversationState.DEPLOYMENT_PLANNING:
            return await self._handle_deployment_planning(context, analysis)
        else:
            return ConversationResponse(
                message="I'm not sure how to help with that right now.",
                response_type="error",
                suggestions=[],
                questions=[],
                actions=[],
                next_state=None,
                confidence=0.1
            )
    
    async def _handle_initial_concept(self, context: ConversationContext, 
                                    analysis: Dict[str, Any]) -> ConversationResponse:
        """Handle initial app concept discussion"""
        
        if analysis['intent'] == 'express_requirement' or analysis['extracted_features']:
            # User has described their app concept
            context.app_concept = context.conversation_history[-2]['message']  # User's message
            context.discovered_features.extend(analysis['extracted_features'])
            
            # Generate encouraging response with concept summary
            concept_summary = self._summarize_concept(context.app_concept, analysis['extracted_features'])
            
            message = f"That sounds like a fantastic idea! 🚀\n\n" \
                     f"From what you've told me, you want to build {concept_summary}. " \
                     f"I can definitely help you create that!\n\n" \
                     f"Let me ask a few questions to make sure I understand exactly what you need..."
            
            # Generate follow-up questions
            questions = self._generate_concept_clarification_questions(analysis)
            
            return ConversationResponse(
                message=message,
                response_type="concept_acknowledgment",
                suggestions=["Tell me more about your users", "What's the main goal of your app?"],
                questions=questions,
                actions=[{"type": "update_concept", "data": {"concept": context.app_concept}}],
                next_state=ConversationState.FEATURE_DISCOVERY,
                confidence=0.8
            )
        
        else:
            # Need more information about the concept
            return ConversationResponse(
                message="Hi there! I'm excited to help you build your app! 😊\n\n" \
                       "To get started, could you tell me about the app you'd like to create? " \
                       "Just describe it in your own words - what should it do and who will use it?",
                response_type="initial_prompt",
                suggestions=[
                    "I want to build a social media app",
                    "I need a business management tool",
                    "I want to create a game",
                    "I'm thinking of an e-commerce platform"
                ],
                questions=[{
                    "type": QuestionType.OPEN_ENDED.value,
                    "question": "What kind of app would you like to build?",
                    "context": "This helps me understand your vision and suggest the right features."
                }],
                actions=[],
                next_state=None,
                confidence=0.7
            )
    
    async def _handle_feature_discovery(self, context: ConversationContext, 
                                      analysis: Dict[str, Any]) -> ConversationResponse:
        """Handle feature discovery and requirements gathering"""
        
        # Add newly discovered features
        new_features = analysis['extracted_features']
        context.discovered_features.extend(new_features)
        
        # Use feature discovery engine to suggest related features
        suggested_features = await self.feature_discovery.suggest_features(
            context.app_concept, context.discovered_features
        )
        
        if analysis['intent'] == 'affirmation':
            # User confirmed a suggested feature
            last_suggestion = self._get_last_suggestion(context)
            if last_suggestion:
                context.discovered_features.append(last_suggestion)
                
                message = f"Great! I've added {last_suggestion} to your app. ✅\n\n" \
                         f"Here are some other features that would work well with what we have so far:"
            else:
                message = "Perfect! Let me suggest some more features that would be great for your app:"
        
        elif analysis['intent'] == 'negation':
            # User declined a suggestion
            message = "No problem! Let's look at some other options that might be a better fit:"
        
        else:
            # Continue feature discovery
            message = f"Excellent! I can see your app is taking shape. 🎯\n\n" \
                     f"Based on what you've told me, I think these features would be valuable:"
        
        # Create feature suggestions with explanations
        feature_suggestions = []
        for feature in suggested_features[:4]:  # Top 4 suggestions
            explanation = self._explain_feature_benefit(feature, context.app_concept)
            feature_suggestions.append(f"**{feature}**: {explanation}")
        
        # Generate next question
        questions = [{
            "type": QuestionType.YES_NO.value,
            "question": f"Would you like to include {suggested_features[0]}?",
            "context": self._explain_feature_benefit(suggested_features[0], context.app_concept)
        }]
        
        # Check if we have enough features to move on
        if len(context.discovered_features) >= 5:
            next_state = ConversationState.COMPONENT_SELECTION
            message += "\n\nI think we have a good foundation! Should we start looking at the technical components?"
            questions.append({
                "type": QuestionType.YES_NO.value,
                "question": "Ready to move on to selecting components?",
                "context": "We'll choose the technical building blocks for your app."
            })
        else:
            next_state = None
        
        return ConversationResponse(
            message=message,
            response_type="feature_discovery",
            suggestions=feature_suggestions,
            questions=questions,
            actions=[{"type": "update_features", "data": {"features": context.discovered_features}}],
            next_state=next_state,
            confidence=0.8
        )
    
    async def _handle_component_selection(self, context: ConversationContext, 
                                        analysis: Dict[str, Any]) -> ConversationResponse:
        """Handle technical component selection"""
        
        # Map features to components
        recommended_components = self._map_features_to_components(context.discovered_features)
        
        if not context.selected_components:
            # First time in component selection
            message = f"Perfect! Now let's choose the technical components (think of them as LEGO blocks) " \
                     f"that will make your app work. 🔧\n\n" \
                     f"Based on your features, I recommend these components:"
            
            component_explanations = []
            for comp in recommended_components[:3]:  # Show top 3
                explanation = self.explanation_generator.explain_component(
                    comp, context.discovered_features, user_friendly=True
                )
                component_explanations.append(f"**{comp['name']}**: {explanation}")
                
            return ConversationResponse(
                message=message,
                response_type="component_introduction",
                suggestions=component_explanations,
                questions=[{
                    "type": QuestionType.YES_NO.value,
                    "question": f"Should we include {recommended_components[0]['name']}?",
                    "context": f"This will handle: {', '.join(recommended_components[0].get('handles', []))}"
                }],
                actions=[],
                next_state=None,
                confidence=0.8
            )
        
        else:
            # Continue component selection
            if analysis['intent'] == 'affirmation':
                # Add the component
                last_suggested = self._get_last_suggested_component(context)
                if last_suggested:
                    context.selected_components.append(last_suggested)
                    
                message = f"Excellent choice! {last_suggested['name']} is now part of your app. ✅\n\n"
            else:
                message = "No problem! Let's look at other options. 🔄\n\n"
            
            # Check if we have enough components
            if len(context.selected_components) >= 4:
                message += "Great! We have the core components. Should we talk about how you want your app to look?"
                
                return ConversationResponse(
                    message=message,
                    response_type="component_completion",
                    suggestions=[
                        "Yes, let's design the interface",
                        "I want to add more technical features",
                        "Can you show me what we have so far?"
                    ],
                    questions=[{
                        "type": QuestionType.YES_NO.value,
                        "question": "Ready to move on to design preferences?",
                        "context": "We'll choose colors, layout, and visual style."
                    }],
                    actions=[{"type": "update_components", "data": {"components": context.selected_components}}],
                    next_state=ConversationState.DESIGN_PREFERENCES,
                    confidence=0.9
                )
            
            else:
                # Continue with more components
                remaining_components = [c for c in recommended_components 
                                     if c not in context.selected_components]
                
                if remaining_components:
                    next_comp = remaining_components[0]
                    message += f"How about {next_comp['name']}?"
                    
                    return ConversationResponse(
                        message=message,
                        response_type="component_suggestion",
                        suggestions=[f"Add {next_comp['name']}", "Skip this component", "Tell me more about this"],
                        questions=[{
                            "type": QuestionType.YES_NO.value,
                            "question": f"Should we include {next_comp['name']}?",
                            "context": self.explanation_generator.explain_component(
                                next_comp, context.discovered_features, user_friendly=True
                            )
                        }],
                        actions=[],
                        next_state=None,
                        confidence=0.8
                    )
        
        # Fallback
        return ConversationResponse(
            message="I'm here to help you choose the right components. What would you like to know?",
            response_type="component_help",
            suggestions=["Explain components to me", "Show me what I have", "Move to next step"],
            questions=[],
            actions=[],
            next_state=None,
            confidence=0.5
        )
    
    async def _handle_design_preferences(self, context: ConversationContext, 
                                       analysis: Dict[str, Any]) -> ConversationResponse:
        """Handle design and visual preferences"""
        
        # Extract design preferences from analysis
        design_prefs = analysis.get('design_preferences', {})
        context.design_preferences.update(design_prefs)
        
        if not context.design_preferences:
            # Start design discussion
            message = f"Awesome! Now let's make your app look amazing! 🎨\n\n" \
                     f"I'll help you choose the visual style that fits your vision. " \
                     f"Think of this as choosing the 'personality' of your app."
            
            return ConversationResponse(
                message=message,
                response_type="design_introduction",
                suggestions=[
                    "Modern and clean",
                    "Fun and colorful", 
                    "Professional and corporate",
                    "Dark and sleek"
                ],
                questions=[{
                    "type": QuestionType.MULTIPLE_CHOICE.value,
                    "question": "What style appeals to you most?",
                    "options": ["Modern & Minimal", "Vibrant & Fun", "Professional", "Dark & Elegant"],
                    "context": "This will determine the overall look and feel of your app."
                }],
                actions=[],
                next_state=None,
                confidence=0.8
            )
        
        else:
            # Continue with specific design elements
            if 'style' not in context.design_preferences:
                # User chose a style
                if analysis['intent'] == 'express_requirement':
                    # Extract style from message
                    style = self._extract_style_preference(context.conversation_history[-2]['message'])
                    context.design_preferences['style'] = style
                    
                    message = f"Perfect! {style} is a great choice. 🎯\n\n" \
                             f"Now let's choose some colors that work well with this style."
                    
                    color_suggestions = self._get_color_suggestions(style)
                    
                    return ConversationResponse(
                        message=message,
                        response_type="color_selection",
                        suggestions=color_suggestions,
                        questions=[{
                            "type": QuestionType.MULTIPLE_CHOICE.value,
                            "question": "Which color palette do you prefer?",
                            "options": color_suggestions,
                            "context": "These colors will be used throughout your app."
                        }],
                        actions=[],
                        next_state=None,
                        confidence=0.8
                    )
            
            elif 'colors' not in context.design_preferences:
                # Handle color selection
                colors = self._extract_color_preference(context.conversation_history[-2]['message'])
                context.design_preferences['colors'] = colors
                
                message = f"Beautiful choice! Your app will look fantastic with those colors. ✨\n\n" \
                         f"I think we have everything we need to start building! " \
                         f"Should we review what we've planned so far?"
                
                return ConversationResponse(
                    message=message,
                    response_type="design_completion",
                    suggestions=[
                        "Yes, show me the summary",
                        "I want to change something",
                        "Let's start building!"
                    ],
                    questions=[{
                        "type": QuestionType.YES_NO.value,
                        "question": "Ready to review your app plan?",
                        "context": "I'll show you everything we've decided and you can make changes if needed."
                    }],
                    actions=[{"type": "update_design", "data": context.design_preferences}],
                    next_state=ConversationState.REVIEW_AND_REFINE,
                    confidence=0.9
                )
        
        # Continue design discussion
        return ConversationResponse(
            message="Let's continue customizing your app's design. What aspect would you like to work on?",
            response_type="design_continuation",
            suggestions=["Choose colors", "Pick fonts", "Layout preferences"],
            questions=[],
            actions=[],
            next_state=None,
            confidence=0.6
        )
    
    async def _handle_review_and_refine(self, context: ConversationContext, 
                                      analysis: Dict[str, Any]) -> ConversationResponse:
        """Handle app review and refinement"""
        
        # Generate comprehensive app summary
        app_summary = self._generate_app_summary(context)
        
        if analysis['intent'] == 'affirmation':
            # User is happy with the plan
            message = f"Fantastic! 🎉 Your app plan is ready.\n\n" \
                     f"I'll start assembling all the components and get everything configured. " \
                     f"This should take just a few minutes!\n\n" \
                     f"While I work, let me know if you want to plan how to launch your app."
            
            return ConversationResponse(
                message=message,
                response_type="build_initiation",
                suggestions=[
                    "Start building now!",
                    "Let's plan the launch",
                    "I want to make a small change"
                ],
                questions=[{
                    "type": QuestionType.YES_NO.value,
                    "question": "Should I start building your app now?",
                    "context": "I'll assemble all the components and configure everything automatically."
                }],
                actions=[{"type": "initiate_build", "data": app_summary}],
                next_state=ConversationState.DEPLOYMENT_PLANNING,
                confidence=0.95
            )
        
        elif analysis['intent'] == 'request_modification':
            # User wants to change something
            message = f"No problem! What would you like to change? 🔧\n\n" \
                     f"You can:\n" \
                     f"• Add or remove features\n" \
                     f"• Change design elements\n" \
                     f"• Modify technical components\n" \
                     f"• Adjust the overall concept"
            
            return ConversationResponse(
                message=message,
                response_type="modification_request",
                suggestions=[
                    "Add a new feature",
                    "Change the design",
                    "Remove a component",
                    "Actually, everything looks good"
                ],
                questions=[{
                    "type": QuestionType.OPEN_ENDED.value,
                    "question": "What would you like to change?",
                    "context": "Just tell me what you'd like to adjust and I'll help you modify it."
                }],
                actions=[],
                next_state=None,
                confidence=0.8
            )
        
        else:
            # Show app summary for review
            message = f"Here's your complete app plan! 📋\n\n{app_summary}\n\n" \
                     f"How does this look? If you're happy with it, we can start building. " \
                     f"If you want to change anything, just let me know!"
            
            return ConversationResponse(
                message=message,
                response_type="app_summary",
                suggestions=[
                    "Looks perfect, let's build it!",
                    "I want to add something",
                    "Can you change the design?",
                    "Remove a feature"
                ],
                questions=[{
                    "type": QuestionType.YES_NO.value,
                    "question": "Are you happy with this plan?",
                    "context": "If yes, I'll start building. If not, tell me what to change."
                }],
                actions=[],
                next_state=None,
                confidence=0.8
            )
    
    async def _handle_deployment_planning(self, context: ConversationContext, 
                                        analysis: Dict[str, Any]) -> ConversationResponse:
        """Handle deployment and launch planning"""
        
        message = f"Your app is being built! 🚀 This is exciting!\n\n" \
                 f"While the technical work happens automatically, let's plan how you want to launch your app. " \
                 f"Do you want to:\n\n" \
                 f"• Share it privately with friends first?\n" \
                 f"• Launch publicly right away?\n" \
                 f"• Test it yourself before others see it?"
        
        return ConversationResponse(
            message=message,
            response_type="deployment_planning",
            suggestions=[
                "Test privately first",
                "Launch publicly",
                "Share with friends only",
                "Just build it for now"
            ],
            questions=[{
                "type": QuestionType.MULTIPLE_CHOICE.value,
                "question": "How would you like to launch your app?",
                "options": ["Private testing", "Public launch", "Friends & family", "Build only"],
                "context": "This determines the initial access and visibility settings."
            }],
            actions=[{"type": "configure_deployment", "data": {}}],
            next_state=ConversationState.COMPLETED,
            confidence=0.9
        )
    
    # Helper methods
    def _initialize_response_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize response templates for different scenarios"""
        
        return {
            'encouragement': [
                "That's a fantastic idea! 🌟",
                "I love where this is going! ✨",
                "Excellent choice! 🎯",
                "Perfect! That will work great! ✅"
            ],
            'clarification': [
                "Just to make sure I understand correctly...",
                "Let me clarify what you're looking for...",
                "To give you the best suggestions...",
                "Help me understand better..."
            ],
            'suggestion_intro': [
                "Based on what you've told me, I think you might also like:",
                "Here are some features that would work well with your app:",
                "I'd recommend adding these complementary features:",
                "These additional features could be valuable:"
            ]
        }
    
    def _initialize_question_patterns(self) -> Dict[str, List[str]]:
        """Initialize question patterns for different topics"""
        
        return {
            'concept_clarification': [
                "Who is your target audience?",
                "What's the main problem your app solves?",
                "How do you envision people using this?",
                "What makes your app unique?"
            ],
            'feature_discovery': [
                "Would users need to create accounts?",
                "Should users be able to share content?",
                "Do you want real-time notifications?",
                "Would offline functionality be important?"
            ],
            'technical_preferences': [
                "Do you need mobile apps or just a website?",
                "How many users do you expect initially?",
                "Do you need payment processing?",
                "Should it integrate with social media?"
            ]
        }
    
    def _initialize_component_knowledge(self) -> Dict[str, Any]:
        """Initialize knowledge about components and their relationships"""
        
        return {
            'user_authentication': {
                'name': 'User Authentication',
                'simple_explanation': 'Lets people create accounts and log in securely',
                'handles': ['user registration', 'login', 'password security'],
                'enables': ['personalization', 'user data', 'privacy'],
                'complexity': 'easy'
            },
            'database': {
                'name': 'Database',
                'simple_explanation': 'Safely stores all your app\'s information',
                'handles': ['data storage', 'information retrieval', 'data backup'],
                'enables': ['remembering user data', 'app content', 'persistent storage'],
                'complexity': 'medium'
            },
            'api_service': {
                'name': 'API Service',
                'simple_explanation': 'Connects your app\'s front-end to the back-end',
                'handles': ['data processing', 'business logic', 'external integrations'],
                'enables': ['app functionality', 'data flow', 'third-party connections'],
                'complexity': 'medium'
            },
            'payment_processing': {
                'name': 'Payment System',
                'simple_explanation': 'Lets customers pay safely through your app',
                'handles': ['credit card processing', 'secure payments', 'refunds'],
                'enables': ['e-commerce', 'subscriptions', 'monetization'],
                'complexity': 'hard'
            }
        }
    
    def _extract_features_from_text(self, text: str) -> List[str]:
        """Extract feature mentions from user text"""
        
        features = []
        text_lower = text.lower()
        
        feature_keywords = {
            'user_accounts': ['user', 'account', 'profile', 'register', 'login', 'sign up'],
            'social_features': ['share', 'social', 'friend', 'follow', 'like', 'comment'],
            'messaging': ['message', 'chat', 'talk', 'communicate', 'send'],
            'notifications': ['notify', 'alert', 'remind', 'notification', 'push'],
            'payments': ['pay', 'buy', 'sell', 'money', 'payment', 'purchase'],
            'photos': ['photo', 'picture', 'image', 'camera', 'upload'],
            'search': ['search', 'find', 'filter', 'look for'],
            'real_time': ['real-time', 'live', 'instant', 'immediately'],
            'analytics': ['track', 'analyze', 'statistics', 'metrics', 'data'],
            'offline': ['offline', 'without internet', 'no connection']
        }
        
        for feature, keywords in feature_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                features.append(feature)
        
        return features
    
    def _extract_component_mentions(self, text: str) -> List[str]:
        """Extract direct component mentions from user text"""
        
        components = []
        text_lower = text.lower()
        
        component_keywords = {
            'database': ['database', 'data storage', 'store data'],
            'authentication': ['login', 'authentication', 'user accounts'],
            'api': ['api', 'backend', 'server'],
            'frontend': ['frontend', 'interface', 'ui'],
            'payments': ['payment', 'checkout', 'billing']
        }
        
        for component, keywords in component_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                components.append(component)
        
        return components
    
    def _extract_design_preferences(self, text: str) -> Dict[str, Any]:
        """Extract design preferences from user text"""
        
        preferences = {}
        text_lower = text.lower()
        
        # Style preferences
        if any(word in text_lower for word in ['modern', 'clean', 'minimal', 'simple']):
            preferences['style_hint'] = 'modern'
        elif any(word in text_lower for word in ['fun', 'colorful', 'bright', 'playful']):
            preferences['style_hint'] = 'playful'
        elif any(word in text_lower for word in ['professional', 'business', 'corporate']):
            preferences['style_hint'] = 'professional'
        elif any(word in text_lower for word in ['dark', 'sleek', 'elegant']):
            preferences['style_hint'] = 'elegant'
        
        # Color preferences
        colors = ['blue', 'green', 'red', 'purple', 'orange', 'yellow', 'pink']
        mentioned_colors = [color for color in colors if color in text_lower]
        if mentioned_colors:
            preferences['color_hints'] = mentioned_colors
        
        return preferences
    
    def _extract_technical_details(self, text: str) -> Dict[str, Any]:
        """Extract technical requirements from user text"""
        
        details = {}
        text_lower = text.lower()
        
        # Platform preferences
        if 'mobile' in text_lower or 'phone' in text_lower:
            details['platforms'] = details.get('platforms', []) + ['mobile']
        if 'web' in text_lower or 'website' in text_lower:
            details['platforms'] = details.get('platforms', []) + ['web']
        
        # Scale hints
        if any(word in text_lower for word in ['many users', 'lots of people', 'thousands']):
            details['scale_hint'] = 'high'
        elif any(word in text_lower for word in ['small', 'few users', 'personal']):
            details['scale_hint'] = 'low'
        
        return details
    
    def _map_features_to_components(self, features: List[str]) -> List[Dict[str, Any]]:
        """Map discovered features to required technical components"""
        
        component_mapping = {
            'user_accounts': ['user_authentication', 'database'],
            'social_features': ['user_authentication', 'database', 'api_service'],
            'messaging': ['user_authentication', 'real_time_messaging', 'database'],
            'payments': ['payment_processing', 'user_authentication', 'database'],
            'photos': ['file_storage', 'image_processing'],
            'notifications': ['push_notifications', 'user_authentication'],
            'search': ['search_engine', 'database'],
            'analytics': ['analytics_service', 'database']
        }
        
        required_components = set()
        for feature in features:
            if feature in component_mapping:
                required_components.update(component_mapping[feature])
        
        # Always include basic components
        required_components.update(['api_service', 'frontend'])
        
        # Convert to component objects
        components = []
        for comp_id in required_components:
            if comp_id in self.component_knowledge:
                comp_info = self.component_knowledge[comp_id].copy()
                comp_info['id'] = comp_id
                components.append(comp_info)
        
        return components
    
    def _generate_app_summary(self, context: ConversationContext) -> str:
        """Generate a comprehensive summary of the planned app"""
        
        summary = f"**🎯 App Concept**: {context.app_concept}\n\n"
        
        if context.discovered_features:
            summary += f"**✨ Key Features**:\n"
            for feature in context.discovered_features:
                summary += f"• {feature.replace('_', ' ').title()}\n"
            summary += "\n"
        
        if context.selected_components:
            summary += f"**🔧 Technical Components**:\n"
            for comp in context.selected_components:
                summary += f"• {comp['name']}: {comp['simple_explanation']}\n"
            summary += "\n"
        
        if context.design_preferences:
            summary += f"**🎨 Design Style**:\n"
            if 'style' in context.design_preferences:
                summary += f"• Style: {context.design_preferences['style'].title()}\n"
            if 'colors' in context.design_preferences:
                summary += f"• Colors: {context.design_preferences['colors']}\n"
            summary += "\n"
        
        summary += f"**🚀 Ready to Build**: All components selected and configured!"
        
        return summary
    
    def _calculate_progress(self, context: ConversationContext) -> Dict[str, Any]:
        """Calculate conversation progress"""
        
        state_progress = {
            ConversationState.INITIAL_CONCEPT: 10,
            ConversationState.FEATURE_DISCOVERY: 30,
            ConversationState.COMPONENT_SELECTION: 50,
            ConversationState.DESIGN_PREFERENCES: 70,
            ConversationState.CONFIGURATION: 80,
            ConversationState.REVIEW_AND_REFINE: 90,
            ConversationState.DEPLOYMENT_PLANNING: 95,
            ConversationState.COMPLETED: 100
        }
        
        base_progress = state_progress.get(context.current_state, 0)
        
        # Add bonus progress for completed items
        bonus = 0
        if context.app_concept:
            bonus += 5
        if len(context.discovered_features) >= 3:
            bonus += 10
        if len(context.selected_components) >= 3:
            bonus += 10
        if context.design_preferences:
            bonus += 5
        
        total_progress = min(100, base_progress + bonus)
        
        return {
            'percentage': total_progress,
            'current_state': context.current_state.value,
            'completed_items': {
                'concept': bool(context.app_concept),
                'features': len(context.discovered_features),
                'components': len(context.selected_components),
                'design': bool(context.design_preferences)
            }
        }

class FeatureDiscoveryEngine:
    """Engine for discovering and suggesting relevant features"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def suggest_features(self, app_concept: str, existing_features: List[str]) -> List[str]:
        """Suggest relevant features based on app concept and existing features"""
        
        concept_lower = app_concept.lower()
        suggestions = []
        
        # App type detection and feature suggestions
        if any(word in concept_lower for word in ['social', 'share', 'community']):
            suggestions.extend([
                'user_profiles', 'friend_connections', 'content_sharing',
                'comments_and_likes', 'messaging', 'notifications'
            ])
        
        elif any(word in concept_lower for word in ['business', 'company', 'work']):
            suggestions.extend([
                'user_roles', 'team_collaboration', 'reporting',
                'analytics', 'integrations', 'admin_panel'
            ])
        
        elif any(word in concept_lower for word in ['game', 'play', 'score']):
            suggestions.extend([
                'leaderboards', 'achievements', 'multiplayer',
                'game_progress', 'rewards', 'challenges'
            ])
        
        elif any(word in concept_lower for word in ['shop', 'buy', 'sell', 'store']):
            suggestions.extend([
                'product_catalog', 'shopping_cart', 'payment_processing',
                'order_management', 'customer_reviews', 'inventory'
            ])
        
        # Remove already selected features
        suggestions = [f for f in suggestions if f not in existing_features]
        
        # Add universal features that might be relevant
        universal_features = [
            'search_functionality', 'offline_support', 'mobile_optimization',
            'data_backup', 'user_settings', 'help_system'
        ]
        
        suggestions.extend([f for f in universal_features if f not in existing_features])
        
        return suggestions[:8]  # Return top 8 suggestions

class ExplanationGenerator:
    """Generates user-friendly explanations for technical concepts"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def explain_component(self, component: Dict[str, Any], 
                         context_features: List[str], user_friendly: bool = True) -> str:
        """Generate explanation for a component based on context"""
        
        base_explanation = component.get('simple_explanation', component.get('name', 'Unknown component'))
        
        if user_friendly:
            # Add context-specific benefits
            benefits = []
            handles = component.get('handles', [])
            
            for feature in context_features:
                if feature == 'user_accounts' and 'user' in str(handles).lower():
                    benefits.append("keeps user data safe and personalized")
                elif feature == 'social_features' and 'data' in str(handles).lower():
                    benefits.append("stores all the content users share")
                elif feature == 'payments' and 'payment' in str(handles).lower():
                    benefits.append("processes payments securely")
            
            if benefits:
                return f"{base_explanation}. For your app, this {benefits[0]}."
            else:
                return base_explanation
        else:
            # Technical explanation
            return f"{base_explanation}. Handles: {', '.join(handles)}"

# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def main():
        logging.basicConfig(level=logging.INFO)
        
        # Initialize conversational app builder
        app_builder = ConversationalAppBuilder()
        
        # Simulate a conversation
        print("=== Conversational App Builder Test ===\n")
        
        # Start conversation
        start_result = await app_builder.start_conversation(
            user_id="test_user",
            initial_message="I want to build a social media app for photographers to share their work"
        )
        
        session_id = start_result['session_id']
        print(f"Assistant: {start_result['response'].message}")
        print(f"Progress: {start_result['progress']['percentage']}%")
        
        # Continue conversation with various user inputs
        test_messages = [
            "Yes, photographers can upload photos and other users can like and comment",
            "I think users should be able to follow each other and create profiles",
            "Yes, that sounds great",
            "I want a modern and clean design",
            "I like blue and white colors",
            "Yes, let's review everything"
        ]
        
        for message in test_messages:
            print(f"\nUser: {message}")
            
            response = await app_builder.continue_conversation(session_id, message)
            
            if 'error' not in response:
                print(f"Assistant: {response['response'].message}")
                print(f"Progress: {response['progress']['percentage']}%")
                print(f"State: {response['conversation_state']}")
                
                if response['response'].questions:
                    print(f"Questions: {len(response['response'].questions)} follow-up questions")
                
                if response.get('app_preview'):
                    print("📱 App preview available!")
            else:
                print(f"Error: {response['error']}")
            
            # Small delay to simulate natural conversation
            await asyncio.sleep(0.1)
        
        print("\n=== Conversation Test Completed ===")
    
    # Run the test
    asyncio.run(main())