"""
Advanced Intent Recognition System
ML-powered natural language understanding for SuperInstance ecosystem
"""

import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel, pipeline
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import json

class IntentType(Enum):
    VISUALIZATION_CHANGE = "visualization_change"      # Affects only what user sees
    APPLICATION_CHANGE = "application_change"         # Affects the actual app being built
    CHARACTER_MANAGEMENT = "character_management"     # Hiring, firing, customizing characters
    WORKFLOW_CONTROL = "workflow_control"             # Pause, speed up, prioritize tasks
    INFORMATION_REQUEST = "information_request"       # Status, explanation, help
    MANUFACTURING_CHANGE = "manufacturing_change"     # Physical product development
    PROCESS_OPTIMIZATION = "process_optimization"     # Manufacturing process improvements
    WORLD_BUILDING = "world_building"                 # DMLog generative world creation
    COMPONENT_REQUEST = "component_request"           # Request specific building blocks
    PERFORMANCE_QUERY = "performance_query"           # Ask about performance metrics

class ContextType(Enum):
    SOFTWARE_DEVELOPMENT = "software_development"
    PHYSICAL_PRODUCT = "physical_product"
    GAME_WORLD_CREATION = "game_world_creation"
    CHARACTER_INTERACTION = "character_interaction"
    SYSTEM_MANAGEMENT = "system_management"

@dataclass
class IntentPrediction:
    intent_type: IntentType
    confidence: float
    context: ContextType
    parameters: Dict[str, Any]
    urgency_level: int  # 1-10 scale
    requires_confirmation: bool

@dataclass
class EntityExtraction:
    entity_type: str
    value: str
    confidence: float
    start_pos: int
    end_pos: int

class MultiModalIntentClassifier(nn.Module):
    """Advanced neural network for intent classification with context awareness"""
    
    def __init__(self, bert_model_name: str = 'distilbert-base-uncased', 
                 num_intents: int = 10, num_contexts: int = 5):
        super().__init__()
        
        # Load pre-trained BERT for text understanding
        self.bert = AutoModel.from_pretrained(bert_model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(bert_model_name)
        
        # Freeze BERT layers (can be unfrozen for fine-tuning)
        for param in self.bert.parameters():
            param.requires_grad = False
        
        # Intent classification head
        self.intent_classifier = nn.Sequential(
            nn.Linear(self.bert.config.hidden_size, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_intents)
        )
        
        # Context classification head
        self.context_classifier = nn.Sequential(
            nn.Linear(self.bert.config.hidden_size, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_contexts)
        )
        
        # Urgency prediction head
        self.urgency_predictor = nn.Sequential(
            nn.Linear(self.bert.config.hidden_size, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid()  # Scale to 0-1, then multiply by 10
        )
        
        # Confidence estimator
        self.confidence_estimator = nn.Sequential(
            nn.Linear(self.bert.config.hidden_size + num_intents + num_contexts, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )
    
    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        # Get BERT embeddings
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.pooler_output
        
        # Classify intent and context
        intent_logits = self.intent_classifier(pooled_output)
        context_logits = self.context_classifier(pooled_output)
        
        # Predict urgency
        urgency = self.urgency_predictor(pooled_output) * 10  # Scale to 1-10
        
        # Estimate confidence
        combined_features = torch.cat([pooled_output, intent_logits, context_logits], dim=-1)
        confidence = self.confidence_estimator(combined_features)
        
        return intent_logits, context_logits, urgency, confidence

class AdvancedIntentRecognitionSystem:
    """Production-ready intent recognition with context awareness and entity extraction"""
    
    def __init__(self, model_path: str = None):
        self.logger = logging.getLogger(__name__)
        
        # Intent and context mappings
        self.intent_to_idx = {intent.value: idx for idx, intent in enumerate(IntentType)}
        self.idx_to_intent = {idx: intent for intent, idx in self.intent_to_idx.items()}
        
        self.context_to_idx = {context.value: idx for idx, context in enumerate(ContextType)}
        self.idx_to_context = {idx: context for context, idx in self.context_to_idx.items()}
        
        # Initialize the neural network
        self.model = MultiModalIntentClassifier(
            num_intents=len(IntentType),
            num_contexts=len(ContextType)
        )
        
        # Named entity recognition pipeline
        self.ner_pipeline = pipeline("ner", 
                                   model="dbmdz/bert-large-cased-finetuned-conll03-english",
                                   aggregation_strategy="simple")
        
        # Load pre-trained weights if available
        if model_path:
            self.load_model(model_path)
        
        # Context history for better predictions
        self.conversation_context = []
        self.user_preferences = {}
        
        # Rule-based patterns for high-confidence matching
        self.intent_patterns = self._initialize_patterns()
        
        self.logger.info("Advanced Intent Recognition System initialized")
    
    def predict_intent(self, user_input: str, user_id: str = None) -> IntentPrediction:
        """
        Predict user intent with high accuracy using hybrid ML + rule-based approach
        """
        self.logger.info(f"Analyzing intent for: '{user_input[:50]}...'")
        
        # First try rule-based patterns for high-confidence cases
        rule_based_result = self._check_rule_patterns(user_input)
        if rule_based_result and rule_based_result.confidence > 0.9:
            self.logger.info(f"High-confidence rule-based match: {rule_based_result.intent_type}")
            return rule_based_result
        
        # Use ML model for complex cases
        ml_result = self._predict_with_ml(user_input, user_id)
        
        # Combine rule-based and ML results
        if rule_based_result and rule_based_result.confidence > 0.7:
            # Blend predictions
            final_confidence = max(rule_based_result.confidence, ml_result.confidence)
            return IntentPrediction(
                intent_type=rule_based_result.intent_type,
                confidence=final_confidence,
                context=ml_result.context,
                parameters=self._merge_parameters(rule_based_result.parameters, ml_result.parameters),
                urgency_level=ml_result.urgency_level,
                requires_confirmation=ml_result.requires_confirmation
            )
        
        return ml_result
    
    def extract_entities(self, text: str) -> List[EntityExtraction]:
        """Extract named entities and domain-specific entities"""
        entities = []
        
        # Use NER pipeline for standard entities
        ner_results = self.ner_pipeline(text)
        
        for result in ner_results:
            entities.append(EntityExtraction(
                entity_type=result['entity_group'],
                value=result['word'],
                confidence=result['score'],
                start_pos=result['start'],
                end_pos=result['end']
            ))
        
        # Custom entity extraction for SuperInstance-specific terms
        custom_entities = self._extract_custom_entities(text)
        entities.extend(custom_entities)
        
        return entities
    
    def update_conversation_context(self, user_input: str, prediction: IntentPrediction):
        """Update conversation context for better future predictions"""
        context_entry = {
            'timestamp': torch.tensor([len(self.conversation_context)]),
            'input': user_input,
            'intent': prediction.intent_type.value,
            'context': prediction.context.value,
            'confidence': prediction.confidence
        }
        
        self.conversation_context.append(context_entry)
        
        # Keep only last 10 entries for efficiency
        if len(self.conversation_context) > 10:
            self.conversation_context = self.conversation_context[-10:]
    
    def _predict_with_ml(self, user_input: str, user_id: str = None) -> IntentPrediction:
        """Use neural network for intent prediction"""
        
        # Tokenize input
        inputs = self.model.tokenizer(
            user_input,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        
        # Get model predictions
        with torch.no_grad():
            intent_logits, context_logits, urgency, confidence = self.model(
                inputs['input_ids'],
                inputs['attention_mask']
            )
        
        # Convert logits to probabilities
        intent_probs = torch.softmax(intent_logits, dim=-1)
        context_probs = torch.softmax(context_logits, dim=-1)
        
        # Get top predictions
        intent_idx = torch.argmax(intent_probs, dim=-1).item()
        context_idx = torch.argmax(context_probs, dim=-1).item()
        
        intent_type = IntentType(self.idx_to_intent[intent_idx])
        context_type = ContextType(self.idx_to_context[context_idx])
        
        # Extract parameters
        parameters = self._extract_parameters(user_input, intent_type, context_type)
        
        # Determine if confirmation is required
        requires_confirmation = self._requires_confirmation(intent_type, confidence.item())
        
        return IntentPrediction(
            intent_type=intent_type,
            confidence=confidence.item(),
            context=context_type,
            parameters=parameters,
            urgency_level=int(urgency.item()),
            requires_confirmation=requires_confirmation
        )
    
    def _check_rule_patterns(self, user_input: str) -> Optional[IntentPrediction]:
        """Check rule-based patterns for high-confidence matching"""
        user_lower = user_input.lower()
        
        for pattern, intent_info in self.intent_patterns.items():
            if any(keyword in user_lower for keyword in pattern):
                confidence = self._calculate_pattern_confidence(user_lower, pattern)
                
                if confidence > 0.6:  # Threshold for rule-based matching
                    return IntentPrediction(
                        intent_type=IntentType(intent_info['intent']),
                        confidence=confidence,
                        context=ContextType(intent_info['context']),
                        parameters=intent_info.get('parameters', {}),
                        urgency_level=intent_info.get('urgency', 5),
                        requires_confirmation=intent_info.get('requires_confirmation', False)
                    )
        
        return None
    
    def _initialize_patterns(self) -> Dict[tuple, Dict[str, Any]]:
        """Initialize rule-based intent patterns"""
        return {
            # Character Management
            ('hire', 'fire', 'character', 'worker'): {
                'intent': 'character_management',
                'context': 'character_interaction',
                'urgency': 3,
                'requires_confirmation': True
            },
            
            # Visualization Changes
            ('change color', 'make prettier', 'animation', 'visual'): {
                'intent': 'visualization_change',
                'context': 'character_interaction',
                'urgency': 2,
                'requires_confirmation': False
            },
            
            # Application Changes
            ('add feature', 'remove function', 'modify app', 'change logic'): {
                'intent': 'application_change',
                'context': 'software_development',
                'urgency': 7,
                'requires_confirmation': True
            },
            
            # Workflow Control
            ('pause', 'stop', 'speed up', 'prioritize'): {
                'intent': 'workflow_control',
                'context': 'system_management',
                'urgency': 6,
                'requires_confirmation': False
            },
            
            # Information Requests
            ('what is', 'how does', 'explain', 'status', 'help'): {
                'intent': 'information_request',
                'context': 'system_management',
                'urgency': 1,
                'requires_confirmation': False
            },
            
            # Manufacturing Changes
            ('assembly', 'fastening', 'manufacturing', 'physical product'): {
                'intent': 'manufacturing_change',
                'context': 'physical_product',
                'urgency': 8,
                'requires_confirmation': True
            },
            
            # World Building
            ('create room', 'add castle', 'generate world', 'build dungeon'): {
                'intent': 'world_building',
                'context': 'game_world_creation',
                'urgency': 5,
                'requires_confirmation': False
            }
        }
    
    def _calculate_pattern_confidence(self, user_input: str, pattern: tuple) -> float:
        """Calculate confidence for rule-based pattern matching"""
        matches = sum(1 for keyword in pattern if keyword in user_input)
        return min(matches / len(pattern) * 1.2, 1.0)  # Boost confidence slightly
    
    def _extract_parameters(self, user_input: str, intent_type: IntentType, 
                           context_type: ContextType) -> Dict[str, Any]:
        """Extract parameters specific to the predicted intent"""
        parameters = {}
        
        if intent_type == IntentType.CHARACTER_MANAGEMENT:
            parameters.update(self._extract_character_parameters(user_input))
        elif intent_type == IntentType.APPLICATION_CHANGE:
            parameters.update(self._extract_app_parameters(user_input))
        elif intent_type == IntentType.MANUFACTURING_CHANGE:
            parameters.update(self._extract_manufacturing_parameters(user_input))
        elif intent_type == IntentType.WORLD_BUILDING:
            parameters.update(self._extract_worldbuilding_parameters(user_input))
        
        return parameters
    
    def _extract_character_parameters(self, user_input: str) -> Dict[str, Any]:
        """Extract character-specific parameters"""
        params = {}
        
        # Character types
        character_types = ['architect', 'wizard', 'designer', 'optimizer', 'analyst']
        for char_type in character_types:
            if char_type in user_input.lower():
                params['character_type'] = char_type
                break
        
        # Actions
        if 'hire' in user_input.lower():
            params['action'] = 'hire'
        elif 'fire' in user_input.lower():
            params['action'] = 'fire'
        elif 'customize' in user_input.lower():
            params['action'] = 'customize'
        
        return params
    
    def _extract_app_parameters(self, user_input: str) -> Dict[str, Any]:
        """Extract application change parameters"""
        params = {}
        
        # Feature types
        if 'database' in user_input.lower():
            params['component_type'] = 'database'
        elif 'ui' in user_input.lower() or 'interface' in user_input.lower():
            params['component_type'] = 'ui'
        elif 'api' in user_input.lower():
            params['component_type'] = 'api'
        
        # Actions
        if 'add' in user_input.lower():
            params['action'] = 'add'
        elif 'remove' in user_input.lower():
            params['action'] = 'remove'
        elif 'modify' in user_input.lower():
            params['action'] = 'modify'
        
        return params
    
    def _extract_manufacturing_parameters(self, user_input: str) -> Dict[str, Any]:
        """Extract manufacturing-specific parameters"""
        params = {}
        
        # Manufacturing processes
        processes = ['assembly', 'welding', 'cutting', 'painting', 'testing']
        for process in processes:
            if process in user_input.lower():
                params['process'] = process
                break
        
        return params
    
    def _extract_worldbuilding_parameters(self, user_input: str) -> Dict[str, Any]:
        """Extract world-building parameters"""
        params = {}
        
        # World elements
        elements = ['room', 'castle', 'dungeon', 'forest', 'city', 'mountain']
        for element in elements:
            if element in user_input.lower():
                params['world_element'] = element
                break
        
        # Genres
        if 'sci-fi' in user_input.lower() or 'scifi' in user_input.lower():
            params['genre'] = 'sci-fi'
        elif 'd&d' in user_input.lower() or 'fantasy' in user_input.lower():
            params['genre'] = 'fantasy'
        elif 'modern' in user_input.lower():
            params['genre'] = 'modern'
        
        return params
    
    def _extract_custom_entities(self, text: str) -> List[EntityExtraction]:
        """Extract SuperInstance-specific entities"""
        entities = []
        
        # Component names
        component_patterns = [
            'auth-service', 'database', 'ui-component', 'api-gateway',
            'redis', 'postgresql', 'react', 'nodejs'
        ]
        
        for pattern in component_patterns:
            if pattern in text.lower():
                start_pos = text.lower().find(pattern)
                end_pos = start_pos + len(pattern)
                
                entities.append(EntityExtraction(
                    entity_type='COMPONENT',
                    value=pattern,
                    confidence=0.9,
                    start_pos=start_pos,
                    end_pos=end_pos
                ))
        
        return entities
    
    def _merge_parameters(self, params1: Dict[str, Any], params2: Dict[str, Any]) -> Dict[str, Any]:
        """Merge parameters from different prediction methods"""
        merged = params1.copy()
        for key, value in params2.items():
            if key not in merged:
                merged[key] = value
        return merged
    
    def _requires_confirmation(self, intent_type: IntentType, confidence: float) -> bool:
        """Determine if the intent requires user confirmation"""
        high_impact_intents = {
            IntentType.APPLICATION_CHANGE,
            IntentType.CHARACTER_MANAGEMENT,
            IntentType.MANUFACTURING_CHANGE
        }
        
        return intent_type in high_impact_intents and confidence < 0.8
    
    def save_model(self, path: str):
        """Save the trained model"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'intent_to_idx': self.intent_to_idx,
            'context_to_idx': self.context_to_idx,
            'conversation_context': self.conversation_context
        }, path)
        self.logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load a pre-trained model"""
        try:
            checkpoint = torch.load(path, map_location='cpu')
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.conversation_context = checkpoint.get('conversation_context', [])
            self.logger.info(f"Model loaded from {path}")
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")

# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize the intent recognition system
    intent_system = AdvancedIntentRecognitionSystem()
    
    # Test cases
    test_inputs = [
        "Fire the infrastructure character, I don't like how slow it works",
        "Make the wizard character more colorful and animated",
        "Add a database component to store user preferences",
        "Pause all workers and show me the current progress",
        "What is the current system performance?",
        "Optimize the assembly process for faster production",
        "Create a castle room with medieval furniture",
        "Build me a fitness app with user authentication"
    ]
    
    for test_input in test_inputs:
        print(f"\n--- Analyzing: '{test_input}' ---")
        prediction = intent_system.predict_intent(test_input)
        
        print(f"Intent: {prediction.intent_type.value}")
        print(f"Context: {prediction.context.value}")
        print(f"Confidence: {prediction.confidence:.3f}")
        print(f"Urgency: {prediction.urgency_level}/10")
        print(f"Requires confirmation: {prediction.requires_confirmation}")
        print(f"Parameters: {prediction.parameters}")
        
        # Extract entities
        entities = intent_system.extract_entities(test_input)
        if entities:
            print(f"Entities: {[(e.entity_type, e.value) for e in entities]}")