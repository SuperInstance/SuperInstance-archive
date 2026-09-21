"""
Intelligent Bot Assembly Engine
Core ML system for autonomous component selection and application assembly
"""

import numpy as np
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel
from typing import List, Dict, Any, Optional, Tuple
import json
import logging
from dataclasses import dataclass
from enum import Enum

class ComponentCategory(Enum):
    UI_INTERFACE = "ui_interface"
    DATA_PROCESSING = "data_processing"
    AUTHENTICATION = "authentication"
    AI_INTEGRATION = "ai_integration"
    DATABASE = "database"
    API_GATEWAY = "api_gateway"
    MONITORING = "monitoring"
    BUSINESS_LOGIC = "business_logic"

@dataclass
class ComponentRequirement:
    category: ComponentCategory
    confidence: float
    priority: int
    constraints: Dict[str, Any]

@dataclass
class ComponentMatch:
    component_id: str
    compatibility_score: float
    performance_prediction: float
    estimated_load: float

class ComponentSelectionNN(nn.Module):
    """Neural network for intelligent component selection"""
    
    def __init__(self, embedding_dim: int = 768, hidden_dim: int = 512):
        super().__init__()
        
        # Requirement encoder
        self.requirement_encoder = nn.Sequential(
            nn.Linear(embedding_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU()
        )
        
        # Component encoder
        self.component_encoder = nn.Sequential(
            nn.Linear(embedding_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU()
        )
        
        # Compatibility predictor
        self.compatibility_head = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 1),
            nn.Sigmoid()
        )
        
        # Performance predictor
        self.performance_head = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 1),
            nn.ReLU()  # Performance score (0+)
        )
        
        # Load predictor
        self.load_head = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 1),
            nn.Sigmoid()  # Normalized load (0-1)
        )
    
    def forward(self, requirement_embeddings: torch.Tensor, 
                component_embeddings: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        
        req_encoded = self.requirement_encoder(requirement_embeddings)
        comp_encoded = self.component_encoder(component_embeddings)
        
        # Combine requirement and component representations
        combined = torch.cat([req_encoded, comp_encoded], dim=-1)
        
        compatibility = self.compatibility_head(combined)
        performance = self.performance_head(combined)
        load = self.load_head(combined)
        
        return compatibility, performance, load

class IntelligentBotAssemblyEngine:
    """Core ML-powered bot assembly engine"""
    
    def __init__(self, model_path: str = None):
        self.logger = logging.getLogger(__name__)
        
        # Initialize language model for requirement understanding
        self.tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
        self.language_model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
        
        # Initialize component selection neural network
        self.component_nn = ComponentSelectionNN()
        
        # Component registry
        self.component_registry = {}
        self.component_embeddings = {}
        
        # Load pre-trained models if available
        if model_path:
            self.load_models(model_path)
        
        self.logger.info("Intelligent Bot Assembly Engine initialized")
    
    def analyze_user_request(self, user_request: str) -> List[ComponentRequirement]:
        """
        Analyze natural language request and extract component requirements
        """
        self.logger.info(f"Analyzing request: {user_request[:100]}...")
        
        # Encode user request
        inputs = self.tokenizer(user_request, return_tensors='pt', 
                               padding=True, truncation=True, max_length=512)
        
        with torch.no_grad():
            outputs = self.language_model(**inputs)
            request_embedding = outputs.last_hidden_state.mean(dim=1)
        
        # Extract requirements using rule-based + ML hybrid approach
        requirements = []
        
        # Analyze for different component categories
        category_keywords = {
            ComponentCategory.UI_INTERFACE: ['interface', 'ui', 'frontend', 'form', 'dashboard', 'chart', 'button'],
            ComponentCategory.DATA_PROCESSING: ['data', 'process', 'analyze', 'calculate', 'transform'],
            ComponentCategory.AUTHENTICATION: ['login', 'auth', 'user', 'permission', 'access', 'security'],
            ComponentCategory.AI_INTEGRATION: ['ai', 'intelligent', 'smart', 'ml', 'predict', 'generate'],
            ComponentCategory.DATABASE: ['store', 'save', 'database', 'persist', 'query'],
            ComponentCategory.API_GATEWAY: ['api', 'endpoint', 'service', 'integration'],
            ComponentCategory.MONITORING: ['monitor', 'track', 'log', 'metric', 'alert'],
            ComponentCategory.BUSINESS_LOGIC: ['business', 'logic', 'rule', 'workflow', 'process']
        }
        
        request_lower = user_request.lower()
        
        for category, keywords in category_keywords.items():
            keyword_count = sum(1 for keyword in keywords if keyword in request_lower)
            if keyword_count > 0:
                confidence = min(keyword_count / len(keywords), 1.0)
                priority = self._calculate_priority(category, keyword_count, request_lower)
                
                requirements.append(ComponentRequirement(
                    category=category,
                    confidence=confidence,
                    priority=priority,
                    constraints=self._extract_constraints(category, user_request)
                ))
        
        # Sort by priority and confidence
        requirements.sort(key=lambda x: (x.priority, x.confidence), reverse=True)
        
        self.logger.info(f"Identified {len(requirements)} component requirements")
        return requirements
    
    def select_optimal_components(self, requirements: List[ComponentRequirement]) -> List[ComponentMatch]:
        """
        Select optimal components using neural network predictions
        """
        self.logger.info("Selecting optimal components...")
        
        matches = []
        
        for requirement in requirements:
            # Find candidates in the same category
            candidates = [comp_id for comp_id, comp_data in self.component_registry.items() 
                         if comp_data.get('category') == requirement.category.value]
            
            if not candidates:
                self.logger.warning(f"No candidates found for category {requirement.category}")
                continue
            
            # Score each candidate
            for candidate_id in candidates:
                if candidate_id not in self.component_embeddings:
                    continue
                
                # Get embeddings
                req_embedding = self._get_requirement_embedding(requirement)
                comp_embedding = self.component_embeddings[candidate_id]
                
                # Predict compatibility, performance, and load
                with torch.no_grad():
                    compatibility, performance, load = self.component_nn(
                        req_embedding.unsqueeze(0),
                        comp_embedding.unsqueeze(0)
                    )
                
                matches.append(ComponentMatch(
                    component_id=candidate_id,
                    compatibility_score=compatibility.item(),
                    performance_prediction=performance.item(),
                    estimated_load=load.item()
                ))
        
        # Sort by compatibility score
        matches.sort(key=lambda x: x.compatibility_score, reverse=True)
        
        self.logger.info(f"Found {len(matches)} component matches")
        return matches
    
    def optimize_assembly_plan(self, matches: List[ComponentMatch]) -> Dict[str, Any]:
        """
        Optimize the assembly plan considering dependencies and resource constraints
        """
        self.logger.info("Optimizing assembly plan...")
        
        # Simple greedy optimization (can be enhanced with more sophisticated algorithms)
        selected_components = []
        total_load = 0.0
        load_limit = 0.8  # Maximum system load threshold
        
        for match in matches:
            if total_load + match.estimated_load <= load_limit:
                selected_components.append(match)
                total_load += match.estimated_load
            elif match.compatibility_score > 0.9:  # High-priority component
                # Find component to replace or add anyway
                selected_components.append(match)
                total_load += match.estimated_load
        
        # Generate deployment order based on dependencies
        deployment_order = self._calculate_deployment_order(selected_components)
        
        assembly_plan = {
            'components': selected_components,
            'deployment_order': deployment_order,
            'estimated_load': total_load,
            'estimated_performance': np.mean([c.performance_prediction for c in selected_components]),
            'confidence_score': np.mean([c.compatibility_score for c in selected_components])
        }
        
        self.logger.info(f"Assembly plan optimized: {len(selected_components)} components, "
                        f"load: {total_load:.2f}, confidence: {assembly_plan['confidence_score']:.2f}")
        
        return assembly_plan
    
    def register_component(self, component_id: str, component_data: Dict[str, Any]):
        """Register a new component in the system"""
        self.component_registry[component_id] = component_data
        
        # Generate embedding for the component
        description = component_data.get('description', '')
        capabilities = ' '.join(component_data.get('capabilities', []))
        combined_text = f"{description} {capabilities}"
        
        inputs = self.tokenizer(combined_text, return_tensors='pt',
                               padding=True, truncation=True, max_length=512)
        
        with torch.no_grad():
            outputs = self.language_model(**inputs)
            embedding = outputs.last_hidden_state.mean(dim=1).squeeze()
            
        self.component_embeddings[component_id] = embedding
        
        self.logger.info(f"Registered component: {component_id}")
    
    def _calculate_priority(self, category: ComponentCategory, keyword_count: int, request: str) -> int:
        """Calculate component priority based on category and context"""
        base_priority = {
            ComponentCategory.AUTHENTICATION: 9,  # Always high priority
            ComponentCategory.DATABASE: 8,
            ComponentCategory.UI_INTERFACE: 7,
            ComponentCategory.BUSINESS_LOGIC: 6,
            ComponentCategory.API_GATEWAY: 5,
            ComponentCategory.AI_INTEGRATION: 4,
            ComponentCategory.DATA_PROCESSING: 3,
            ComponentCategory.MONITORING: 2
        }
        
        priority = base_priority.get(category, 1)
        
        # Boost priority based on keyword frequency
        priority += min(keyword_count, 3)
        
        return min(priority, 10)
    
    def _extract_constraints(self, category: ComponentCategory, request: str) -> Dict[str, Any]:
        """Extract specific constraints from the request"""
        constraints = {}
        
        # Performance constraints
        if 'fast' in request.lower() or 'quick' in request.lower():
            constraints['performance_priority'] = 'high'
        
        # Security constraints
        if 'secure' in request.lower() or 'encrypted' in request.lower():
            constraints['security_level'] = 'high'
        
        # Scale constraints
        if 'many users' in request.lower() or 'scale' in request.lower():
            constraints['scalability'] = 'high'
        
        return constraints
    
    def _get_requirement_embedding(self, requirement: ComponentRequirement) -> torch.Tensor:
        """Generate embedding for a requirement"""
        req_text = f"{requirement.category.value} priority {requirement.priority} confidence {requirement.confidence}"
        
        inputs = self.tokenizer(req_text, return_tensors='pt',
                               padding=True, truncation=True, max_length=512)
        
        with torch.no_grad():
            outputs = self.language_model(**inputs)
            embedding = outputs.last_hidden_state.mean(dim=1).squeeze()
        
        return embedding
    
    def _calculate_deployment_order(self, components: List[ComponentMatch]) -> List[str]:
        """Calculate optimal deployment order based on dependencies"""
        # Simplified dependency resolution
        dependency_order = [
            ComponentCategory.DATABASE,
            ComponentCategory.AUTHENTICATION,
            ComponentCategory.API_GATEWAY,
            ComponentCategory.BUSINESS_LOGIC,
            ComponentCategory.AI_INTEGRATION,
            ComponentCategory.DATA_PROCESSING,
            ComponentCategory.UI_INTERFACE,
            ComponentCategory.MONITORING
        ]
        
        ordered_components = []
        
        for category in dependency_order:
            category_components = [c for c in components 
                                 if self.component_registry.get(c.component_id, {}).get('category') == category.value]
            ordered_components.extend([c.component_id for c in category_components])
        
        return ordered_components
    
    def save_models(self, path: str):
        """Save trained models"""
        torch.save({
            'component_nn_state_dict': self.component_nn.state_dict(),
            'component_registry': self.component_registry,
        }, path)
        self.logger.info(f"Models saved to {path}")
    
    def load_models(self, path: str):
        """Load pre-trained models"""
        try:
            checkpoint = torch.load(path, map_location='cpu')
            self.component_nn.load_state_dict(checkpoint['component_nn_state_dict'])
            self.component_registry = checkpoint.get('component_registry', {})
            self.logger.info(f"Models loaded from {path}")
        except Exception as e:
            self.logger.error(f"Failed to load models: {e}")

# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize the assembly engine
    engine = IntelligentBotAssemblyEngine()
    
    # Register some example components
    engine.register_component("auth-jwt", {
        "category": "authentication",
        "description": "JWT-based authentication system",
        "capabilities": ["login", "logout", "token_validation", "user_management"],
        "dependencies": ["database"],
        "performance_rating": 0.9,
        "load_factor": 0.2
    })
    
    engine.register_component("postgres-db", {
        "category": "database",
        "description": "PostgreSQL database with vector support",
        "capabilities": ["sql_queries", "vector_search", "transactions", "backups"],
        "dependencies": [],
        "performance_rating": 0.95,
        "load_factor": 0.4
    })
    
    engine.register_component("react-dashboard", {
        "category": "ui_interface",
        "description": "Modern React dashboard with charts",
        "capabilities": ["charts", "tables", "forms", "responsive_design"],
        "dependencies": ["api_gateway"],
        "performance_rating": 0.85,
        "load_factor": 0.3
    })
    
    # Test with example request
    user_request = "Build me a fitness app with user login and dashboard to track workouts"
    
    # Analyze request
    requirements = engine.analyze_user_request(user_request)
    print(f"Requirements: {[r.category.value for r in requirements]}")
    
    # Select components
    matches = engine.select_optimal_components(requirements)
    print(f"Component matches: {len(matches)}")
    
    # Optimize assembly plan
    plan = engine.optimize_assembly_plan(matches)
    print(f"Assembly plan confidence: {plan['confidence_score']:.2f}")
    print(f"Deployment order: {plan['deployment_order']}")