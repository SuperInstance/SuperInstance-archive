"""
Chatbot-Driven Development Interface
AI-powered natural language interface for UI development
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime
import json
import uuid
import re
import asyncio

class ChatMessage(BaseModel):
    """Chat message in the development conversation"""
    id: str
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}

class ComponentSuggestion(BaseModel):
    """AI-suggested component"""
    id: str
    type: str
    properties: Dict[str, Any]
    position: Optional[Tuple[float, float]] = None
    confidence: float
    reasoning: str

class CodeGeneration(BaseModel):
    """Generated code from natural language"""
    id: str
    language: str
    code: str
    description: str
    dependencies: List[str] = []
    confidence: float

class ConversationContext(BaseModel):
    """Context for development conversation"""
    id: str
    project_name: str
    messages: List[ChatMessage]
    current_components: List[Dict[str, Any]] = []
    generated_code: List[CodeGeneration] = []
    suggestions: List[ComponentSuggestion] = []
    metadata: Dict[str, Any] = {}

class IntentClassification(BaseModel):
    """Classification of user intent"""
    intent: str
    confidence: float
    entities: Dict[str, Any]
    parameters: Dict[str, Any]

class ChatbotDevelopmentInterface:
    """AI-powered chatbot for UI development"""
    
    def __init__(self):
        self.conversations: Dict[str, ConversationContext] = {}
        self.component_templates = self._load_component_templates()
        self.intent_patterns = self._load_intent_patterns()
        self.code_templates = self._load_code_templates()
        
    def _load_component_templates(self) -> Dict[str, Dict]:
        """Load component templates for suggestions"""
        return {
            "button": {
                "properties": ["label", "variant", "size", "color", "disabled", "onClick"],
                "required": ["label"],
                "examples": ["Submit", "Cancel", "Save", "Delete"],
                "variants": ["primary", "secondary", "success", "danger", "warning"]
            },
            "input": {
                "properties": ["placeholder", "type", "value", "required", "disabled", "validation"],
                "required": ["placeholder"],
                "types": ["text", "email", "password", "number", "date", "tel"],
                "examples": ["Enter your name", "Email address", "Password"]
            },
            "form": {
                "properties": ["title", "fields", "onSubmit", "validation"],
                "contains": ["input", "button", "select", "checkbox"],
                "examples": ["Contact Form", "Registration Form", "Login Form"]
            },
            "table": {
                "properties": ["columns", "data", "sortable", "filterable", "pagination"],
                "required": ["columns"],
                "examples": ["User List", "Product Catalog", "Order History"]
            },
            "chart": {
                "properties": ["type", "data", "width", "height", "title", "legend"],
                "types": ["line", "bar", "pie", "area", "scatter"],
                "examples": ["Sales Chart", "User Analytics", "Performance Metrics"]
            },
            "card": {
                "properties": ["title", "content", "image", "actions"],
                "examples": ["Product Card", "User Profile", "News Article"]
            },
            "modal": {
                "properties": ["title", "content", "size", "closable", "onClose"],
                "sizes": ["small", "medium", "large", "fullscreen"],
                "examples": ["Confirmation Dialog", "Edit Form", "Image Viewer"]
            },
            "navigation": {
                "properties": ["items", "orientation", "variant"],
                "orientations": ["horizontal", "vertical"],
                "variants": ["tabs", "pills", "breadcrumb", "sidebar"]
            },
            "dropdown": {
                "properties": ["options", "placeholder", "searchable", "multiple"],
                "examples": ["Select Country", "Choose Category", "Pick Tags"]
            },
            "checkbox": {
                "properties": ["label", "checked", "disabled", "indeterminate"],
                "examples": ["I agree to terms", "Enable notifications", "Remember me"]
            }
        }
    
    def _load_intent_patterns(self) -> Dict[str, List[str]]:
        """Load intent recognition patterns"""
        return {
            "create_component": [
                r"create (?:a )?(.+)",
                r"add (?:a )?(.+)",
                r"make (?:a )?(.+)",
                r"build (?:a )?(.+)",
                r"i want (?:a )?(.+)",
                r"i need (?:a )?(.+)",
                r"can you (?:create|add|make) (?:a )?(.+)"
            ],
            "modify_component": [
                r"change (?:the )?(.+)",
                r"modify (?:the )?(.+)",
                r"update (?:the )?(.+)",
                r"edit (?:the )?(.+)",
                r"make (?:the )?(.+) (.+)",
                r"set (?:the )?(.+) to (.+)"
            ],
            "style_component": [
                r"make (?:it|the .+) (.+) color",
                r"change (?:the )?color to (.+)",
                r"make (?:it|the .+) bigger",
                r"make (?:it|the .+) smaller",
                r"style (?:the )?(.+)",
                r"apply (.+) theme"
            ],
            "layout_components": [
                r"put (?:the )?(.+) (?:on the|to the) (.+)",
                r"move (?:the )?(.+) (.+)",
                r"align (?:the )?(.+) (.+)",
                r"center (?:the )?(.+)",
                r"arrange (?:the )?(.+)"
            ],
            "connect_components": [
                r"connect (?:the )?(.+) to (?:the )?(.+)",
                r"link (?:the )?(.+) (?:with|to) (?:the )?(.+)",
                r"when (?:the )?(.+) (.+), (.+)",
                r"make (?:the )?(.+) trigger (.+)"
            ],
            "generate_code": [
                r"generate (?:the )?code",
                r"show me (?:the )?code",
                r"export (?:to )?(.+)",
                r"create (.+) code",
                r"write (?:the )?(.+) implementation"
            ],
            "explain": [
                r"explain (?:the )?(.+)",
                r"what (?:is|does) (?:the )?(.+)",
                r"how (?:does|do) (?:the )?(.+) work",
                r"tell me about (.+)"
            ]
        }
    
    def _load_code_templates(self) -> Dict[str, str]:
        """Load code generation templates"""
        return {
            "react_component": """
import React from 'react';

const {component_name} = ({{ {props} }}) => {{
  return (
    <div className="{class_name}">
      {content}
    </div>
  );
}};

export default {component_name};
""",
            "vue_component": """
<template>
  <div class="{class_name}">
    {content}
  </div>
</template>

<script>
export default {{
  name: '{component_name}',
  props: {{
    {props}
  }}
}};
</script>

<style scoped>
{styles}
</style>
""",
            "html": """
<div class="{class_name}" id="{id}">
  {content}
</div>
""",
            "css": """
.{class_name} {{
  {styles}
}}
""",
            "javascript": """
class {component_name} {{
  constructor(options) {{
    this.element = options.element;
    this.props = options.props || {{}};
    this.init();
  }}
  
  init() {{
    {init_code}
  }}
  
  {methods}
}}
"""
        }
    
    def create_conversation(self, project_name: str) -> str:
        """Create a new development conversation"""
        conversation_id = str(uuid.uuid4())
        
        # Add welcome message
        welcome_message = ChatMessage(
            id=str(uuid.uuid4()),
            role="assistant",
            content=f"Hello! I'm here to help you build the UI for '{project_name}'. You can describe what you want to create in natural language, and I'll help you build it step by step. What would you like to start with?",
            timestamp=datetime.now(),
            metadata={"type": "welcome"}
        )
        
        conversation = ConversationContext(
            id=conversation_id,
            project_name=project_name,
            messages=[welcome_message],
            metadata={"created_at": datetime.now().isoformat()}
        )
        
        self.conversations[conversation_id] = conversation
        return conversation_id
    
    def process_message(self, conversation_id: str, message: str) -> Dict[str, Any]:
        """Process user message and generate response"""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        conversation = self.conversations[conversation_id]
        
        # Add user message
        user_message = ChatMessage(
            id=str(uuid.uuid4()),
            role="user",
            content=message,
            timestamp=datetime.now()
        )
        conversation.messages.append(user_message)
        
        # Classify intent
        intent = self._classify_intent(message)
        
        # Generate response based on intent
        response = self._generate_response(conversation, intent, message)
        
        # Add assistant message
        assistant_message = ChatMessage(
            id=str(uuid.uuid4()),
            role="assistant",
            content=response.get("message", "I understand. Let me help you with that."),
            timestamp=datetime.now(),
            metadata={"intent": intent.dict(), "suggestions": response.get("suggestions", [])}
        )
        conversation.messages.append(assistant_message)
        
        return response
    
    def _classify_intent(self, message: str) -> IntentClassification:
        """Classify user intent from message"""
        message_lower = message.lower().strip()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, message_lower)
                if match:
                    entities = {}
                    parameters = {}
                    
                    # Extract entities from regex groups
                    groups = match.groups()
                    if groups:
                        if intent == "create_component":
                            entities["component_type"] = self._extract_component_type(groups[0])
                            entities["description"] = groups[0]
                        elif intent == "modify_component":
                            entities["target"] = groups[0] if len(groups) > 0 else ""
                            entities["modification"] = groups[1] if len(groups) > 1 else ""
                        elif intent == "style_component":
                            entities["property"] = groups[0] if len(groups) > 0 else ""
                            entities["value"] = groups[1] if len(groups) > 1 else ""
                        elif intent == "layout_components":
                            entities["component"] = groups[0] if len(groups) > 0 else ""
                            entities["position"] = groups[1] if len(groups) > 1 else ""
                    
                    return IntentClassification(
                        intent=intent,
                        confidence=0.8,  # Simplified confidence scoring
                        entities=entities,
                        parameters=parameters
                    )
        
        # Default intent if no match
        return IntentClassification(
            intent="general",
            confidence=0.5,
            entities={},
            parameters={}
        )
    
    def _extract_component_type(self, description: str) -> str:
        """Extract component type from description"""
        description_lower = description.lower()
        
        # Direct matches
        for component_type in self.component_templates.keys():
            if component_type in description_lower:
                return component_type
        
        # Keyword matches
        if any(word in description_lower for word in ["form", "input", "field"]):
            return "form"
        elif any(word in description_lower for word in ["button", "click", "submit"]):
            return "button"
        elif any(word in description_lower for word in ["table", "list", "grid", "data"]):
            return "table"
        elif any(word in description_lower for word in ["chart", "graph", "visualization"]):
            return "chart"
        elif any(word in description_lower for word in ["card", "panel", "box"]):
            return "card"
        elif any(word in description_lower for word in ["modal", "dialog", "popup"]):
            return "modal"
        elif any(word in description_lower for word in ["nav", "menu", "navigation"]):
            return "navigation"
        elif any(word in description_lower for word in ["dropdown", "select", "option"]):
            return "dropdown"
        
        return "container"  # Default fallback
    
    def _generate_response(self, conversation: ConversationContext, 
                          intent: IntentClassification, message: str) -> Dict[str, Any]:
        """Generate response based on intent and context"""
        
        if intent.intent == "create_component":
            return self._handle_create_component(conversation, intent, message)
        elif intent.intent == "modify_component":
            return self._handle_modify_component(conversation, intent, message)
        elif intent.intent == "style_component":
            return self._handle_style_component(conversation, intent, message)
        elif intent.intent == "layout_components":
            return self._handle_layout_components(conversation, intent, message)
        elif intent.intent == "connect_components":
            return self._handle_connect_components(conversation, intent, message)
        elif intent.intent == "generate_code":
            return self._handle_generate_code(conversation, intent, message)
        elif intent.intent == "explain":
            return self._handle_explain(conversation, intent, message)
        else:
            return self._handle_general(conversation, intent, message)
    
    def _handle_create_component(self, conversation: ConversationContext, 
                                intent: IntentClassification, message: str) -> Dict[str, Any]:
        """Handle component creation requests"""
        component_type = intent.entities.get("component_type", "container")
        description = intent.entities.get("description", "")
        
        # Get template for component type
        template = self.component_templates.get(component_type, {})
        
        # Generate component properties based on description
        properties = self._infer_properties(component_type, description, template)
        
        # Create component suggestion
        suggestion = ComponentSuggestion(
            id=str(uuid.uuid4()),
            type=component_type,
            properties=properties,
            confidence=0.8,
            reasoning=f"Based on your request to create '{description}', I'm suggesting a {component_type} component with these properties."
        )
        
        conversation.suggestions.append(suggestion)
        
        # Add to current components
        component_data = {
            "id": suggestion.id,
            "type": component_type,
            "properties": properties,
            "created_from": "chatbot",
            "description": description
        }
        conversation.current_components.append(component_data)
        
        response_message = f"I've created a {component_type} component for you"
        if properties:
            prop_list = [f"{k}: {v}" for k, v in properties.items()]
            response_message += f" with the following properties: {', '.join(prop_list)}"
        
        response_message += ". Would you like me to modify anything or add more components?"
        
        return {
            "message": response_message,
            "suggestions": [suggestion.dict()],
            "components": [component_data],
            "action": "component_created"
        }
    
    def _infer_properties(self, component_type: str, description: str, 
                         template: Dict[str, Any]) -> Dict[str, Any]:
        """Infer component properties from description"""
        properties = {}
        description_lower = description.lower()
        
        if component_type == "button":
            # Extract button label
            label_patterns = [r"'([^']+)'", r'"([^"]+)"', r"button (?:called |labeled )?(.+)"]
            for pattern in label_patterns:
                match = re.search(pattern, description_lower)
                if match:
                    properties["label"] = match.group(1).strip()
                    break
            else:
                properties["label"] = "Button"
            
            # Infer variant
            if any(word in description_lower for word in ["submit", "save", "confirm"]):
                properties["variant"] = "primary"
            elif any(word in description_lower for word in ["cancel", "close"]):
                properties["variant"] = "secondary"
            elif any(word in description_lower for word in ["delete", "remove"]):
                properties["variant"] = "danger"
        
        elif component_type == "input":
            # Extract placeholder
            placeholder_patterns = [r"placeholder ['\"]([^'\"]+)['\"]", r"for (.+)"]
            for pattern in placeholder_patterns:
                match = re.search(pattern, description_lower)
                if match:
                    properties["placeholder"] = match.group(1).strip()
                    break
            else:
                properties["placeholder"] = "Enter value"
            
            # Infer input type
            if any(word in description_lower for word in ["email", "mail"]):
                properties["type"] = "email"
            elif any(word in description_lower for word in ["password", "pass"]):
                properties["type"] = "password"
            elif any(word in description_lower for word in ["number", "numeric"]):
                properties["type"] = "number"
            elif any(word in description_lower for word in ["date"]):
                properties["type"] = "date"
        
        elif component_type == "table":
            properties["columns"] = ["Column 1", "Column 2", "Column 3"]
            properties["sortable"] = True
            if "search" in description_lower:
                properties["filterable"] = True
        
        elif component_type == "chart":
            # Infer chart type
            if any(word in description_lower for word in ["line", "trend"]):
                properties["type"] = "line"
            elif any(word in description_lower for word in ["bar", "column"]):
                properties["type"] = "bar"
            elif any(word in description_lower for word in ["pie", "donut"]):
                properties["type"] = "pie"
            else:
                properties["type"] = "line"  # Default
        
        elif component_type == "form":
            # Extract form title
            title_patterns = [r"form (?:called |titled )?['\"]([^'\"]+)['\"]", r"(.+) form"]
            for pattern in title_patterns:
                match = re.search(pattern, description_lower)
                if match:
                    properties["title"] = match.group(1).strip().title()
                    break
            else:
                properties["title"] = "Form"
        
        return properties
    
    def _handle_modify_component(self, conversation: ConversationContext, 
                                intent: IntentClassification, message: str) -> Dict[str, Any]:
        """Handle component modification requests"""
        target = intent.entities.get("target", "")
        modification = intent.entities.get("modification", "")
        
        # Find the component to modify
        target_component = None
        for component in conversation.current_components:
            if (target.lower() in component.get("description", "").lower() or 
                target.lower() in component.get("type", "").lower()):
                target_component = component
                break
        
        if not target_component:
            return {
                "message": f"I couldn't find a component matching '{target}'. Could you be more specific about which component you want to modify?",
                "action": "clarification_needed"
            }
        
        # Apply modification
        old_properties = target_component["properties"].copy()
        self._apply_modification(target_component, modification, message)
        
        return {
            "message": f"I've updated the {target_component['type']} component. The modification has been applied.",
            "components": [target_component],
            "action": "component_modified",
            "changes": {
                "before": old_properties,
                "after": target_component["properties"]
            }
        }
    
    def _apply_modification(self, component: Dict[str, Any], modification: str, message: str):
        """Apply modification to component"""
        message_lower = message.lower()
        properties = component["properties"]
        
        # Color modifications
        color_match = re.search(r"(?:color|colour) (?:to )?([a-zA-Z]+|#[0-9a-fA-F]{6})", message_lower)
        if color_match:
            properties["color"] = color_match.group(1)
        
        # Size modifications
        if "bigger" in message_lower or "larger" in message_lower:
            properties["size"] = "large"
        elif "smaller" in message_lower:
            properties["size"] = "small"
        
        # Text modifications
        text_match = re.search(r"(?:text|label) (?:to )?['\"]([^'\"]+)['\"]", message_lower)
        if text_match:
            if "label" in properties:
                properties["label"] = text_match.group(1)
            elif "placeholder" in properties:
                properties["placeholder"] = text_match.group(1)
    
    def _handle_style_component(self, conversation: ConversationContext, 
                               intent: IntentClassification, message: str) -> Dict[str, Any]:
        """Handle styling requests"""
        return {
            "message": "I can help you style the components. What specific styling would you like to apply?",
            "action": "style_applied"
        }
    
    def _handle_layout_components(self, conversation: ConversationContext, 
                                 intent: IntentClassification, message: str) -> Dict[str, Any]:
        """Handle layout requests"""
        return {
            "message": "I can help you arrange the components. What layout would you like?",
            "action": "layout_applied"
        }
    
    def _handle_connect_components(self, conversation: ConversationContext, 
                                  intent: IntentClassification, message: str) -> Dict[str, Any]:
        """Handle component connection requests"""
        return {
            "message": "I can help you connect components with interactions. What should happen when users interact with these components?",
            "action": "components_connected"
        }
    
    def _handle_generate_code(self, conversation: ConversationContext, 
                             intent: IntentClassification, message: str) -> Dict[str, Any]:
        """Handle code generation requests"""
        # Determine target language/framework
        language = "react"  # Default
        if "vue" in message.lower():
            language = "vue"
        elif "html" in message.lower():
            language = "html"
        elif "javascript" in message.lower():
            language = "javascript"
        
        # Generate code for current components
        generated_code = []
        for component in conversation.current_components:
            code = self._generate_component_code(component, language)
            generated_code.append(code)
        
        conversation.generated_code.extend(generated_code)
        
        return {
            "message": f"I've generated {language.title()} code for your components. You can view and download the code.",
            "code": generated_code,
            "action": "code_generated"
        }
    
    def _generate_component_code(self, component: Dict[str, Any], language: str) -> CodeGeneration:
        """Generate code for a component"""
        component_type = component["type"]
        properties = component["properties"]
        
        template = self.code_templates.get(f"{language}_component", self.code_templates["html"])
        
        # Prepare template variables
        component_name = f"{component_type.title()}Component"
        class_name = f"{component_type}-component"
        
        # Generate props
        props = []
        for key, value in properties.items():
            if language == "react":
                props.append(f"{key} = '{value}'")
            elif language == "vue":
                props.append(f"{key}: String")
        
        props_str = ", ".join(props) if props else ""
        
        # Generate content based on component type
        content = self._generate_component_content(component_type, properties, language)
        
        # Fill template
        code = template.format(
            component_name=component_name,
            class_name=class_name,
            props=props_str,
            content=content,
            id=component["id"],
            styles="/* Add your styles here */"
        )
        
        return CodeGeneration(
            id=str(uuid.uuid4()),
            language=language,
            code=code,
            description=f"{component_type} component in {language}",
            confidence=0.8
        )
    
    def _generate_component_content(self, component_type: str, properties: Dict[str, Any], 
                                   language: str) -> str:
        """Generate component content based on type"""
        if component_type == "button":
            label = properties.get("label", "Button")
            if language == "html":
                return f'<button>{label}</button>'
            else:
                return f'<button>{{{label}}}</button>'
        
        elif component_type == "input":
            placeholder = properties.get("placeholder", "Enter value")
            input_type = properties.get("type", "text")
            if language == "html":
                return f'<input type="{input_type}" placeholder="{placeholder}" />'
            else:
                return f'<input type="{input_type}" :placeholder="{placeholder}" />'
        
        elif component_type == "table":
            return "<table><thead><tr><th>Column 1</th><th>Column 2</th></tr></thead><tbody></tbody></table>"
        
        else:
            return f"<div><!-- {component_type} content --></div>"
    
    def _handle_explain(self, conversation: ConversationContext, 
                       intent: IntentClassification, message: str) -> Dict[str, Any]:
        """Handle explanation requests"""
        return {
            "message": "I can explain how components work and help you understand the UI building process. What would you like me to explain?",
            "action": "explanation_provided"
        }
    
    def _handle_general(self, conversation: ConversationContext, 
                       intent: IntentClassification, message: str) -> Dict[str, Any]:
        """Handle general conversation"""
        return {
            "message": "I'm here to help you build UI components. You can ask me to create forms, buttons, tables, charts, and more. Just describe what you need in natural language!",
            "action": "general_response"
        }
    
    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get summary of conversation and created components"""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        conversation = self.conversations[conversation_id]
        
        return {
            "id": conversation_id,
            "project_name": conversation.project_name,
            "message_count": len(conversation.messages),
            "components_created": len(conversation.current_components),
            "code_generated": len(conversation.generated_code),
            "suggestions": len(conversation.suggestions),
            "components": conversation.current_components,
            "latest_code": conversation.generated_code[-1].dict() if conversation.generated_code else None
        }
    
    def export_conversation(self, conversation_id: str) -> Dict:
        """Export conversation data"""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        conversation = self.conversations[conversation_id]
        
        return {
            "conversation": conversation.dict(),
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        }
    
    def list_conversations(self) -> List[Dict]:
        """List all conversations"""
        return [
            {
                "id": conv.id,
                "project_name": conv.project_name,
                "message_count": len(conv.messages),
                "component_count": len(conv.current_components),
                "last_updated": conv.messages[-1].timestamp.isoformat() if conv.messages else None
            }
            for conv in self.conversations.values()
        ]