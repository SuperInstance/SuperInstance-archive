# src/bots/research_bots.py
"""
Background Research Bots - Use cheap/free models for preparatory work
Run in parallel with main content creation agents
"""

from .base_bot import BaseBot, BotConfig
from typing import Dict, Any
import json


class BackgroundResearcherBot(BaseBot):
    """
    Lightweight research bot that uses cheap models (Groq free tier)
    Runs in background to prepare information for main agents
    """

    async def build_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        research_type = task.get('type', 'general')
        target = task.get('target', '')

        if research_type == 'character_analysis':
            return self._character_analysis_prompt(task, context)
        elif research_type == 'scene_breakdown':
            return self._scene_breakdown_prompt(task, context)
        elif research_type == 'location_catalog':
            return self._location_catalog_prompt(task, context)
        elif research_type == 'theme_extraction':
            return self._theme_extraction_prompt(task, context)
        else:
            return self._general_research_prompt(task, context)

    def _character_analysis_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        character_name = task.get('character', '')
        story_content = task.get('story_content', '')

        return f"""Analyze this character from the story:

Character: {character_name}

Story excerpt:
{story_content[:3000]}

Provide a detailed character profile as JSON:
{{
  "name": "{character_name}",
  "age": "...",
  "appearance": "Physical description",
  "personality": "Key personality traits",
  "motivations": "What drives this character",
  "relationships": "Key relationships with other characters",
  "arc": "Character development arc",
  "speech_patterns": "How they talk, common phrases",
  "memorable_moments": ["moment 1", "moment 2"],
  "notes_for_adaptation": "Important things to remember when adapting"
}}
"""

    def _scene_breakdown_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        story_content = task.get('story_content', '')

        return f"""Break this story into distinct scenes for video adaptation.

Story:
{story_content[:4000]}

Identify all scenes and provide as JSON:
{{
  "scenes": [
    {{
      "number": 1,
      "title": "Scene title",
      "location": "Where it takes place",
      "time": "Day/night, time period",
      "characters": ["character 1", "character 2"],
      "key_action": "What happens in this scene",
      "emotional_tone": "Happy/tense/mysterious/etc",
      "duration_estimate": "2-3 minutes",
      "visual_notes": "Important visual elements"
    }},
    ...
  ],
  "total_scenes": 10
}}
"""

    def _location_catalog_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        story_content = task.get('story_content', '')

        return f"""Extract all unique locations from this story.

Story:
{story_content[:3000]}

List all locations as JSON:
{{
  "locations": [
    {{
      "name": "Location name",
      "type": "interior/exterior",
      "description": "Detailed visual description",
      "atmosphere": "Cozy/ominous/busy/quiet/etc",
      "key_features": ["feature 1", "feature 2"],
      "appears_in_scenes": [1, 3, 7]
    }},
    ...
  ]
}}
"""

    def _theme_extraction_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        story_content = task.get('story_content', '')

        return f"""Identify the key themes in this story.

Story:
{story_content[:4000]}

Extract themes as JSON:
{{
  "primary_themes": [
    {{
      "theme": "Theme name",
      "description": "How this theme is explored",
      "key_moments": ["moment 1", "moment 2"]
    }}
  ],
  "secondary_themes": [...],
  "symbols": [
    {{
      "symbol": "Object or concept",
      "meaning": "What it represents",
      "appearances": ["where it shows up"]
    }}
  ],
  "overall_message": "The story's core message"
}}
"""

    def _general_research_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        description = task.get('description', '')
        data = task.get('data', {})

        # Build lightweight context summary (don't dump entire context)
        context_summary = {
            "project_id": context.get("project_id", "default"),
            "story_count": context.get("story_count", 0)
        }

        return f"""Research task: {description}

Context: Working with {context_summary['story_count']} relevant stories from the Loopless universe.

Data:
{json.dumps(data, indent=2)[:1000]}

Provide thorough research results as JSON with these fields:
{{
  "findings": "Main findings from research",
  "details": {{}},
  "recommendations": []
}}
"""

    def validate_response(self, response: str) -> bool:
        try:
            data = json.loads(response.strip().strip('```json').strip('```'))
            return True
        except:
            return False

    async def do_continuous_work(self):
        pass  # Not always-running


class SummarizerBot(BaseBot):
    """
    Condenses large content into summaries
    Uses cheap models for quick summarization
    """

    async def build_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        content = task.get('content', '')
        summary_type = task.get('summary_type', 'general')
        target_length = task.get('target_length', 'medium')

        length_guidance = {
            'short': '1-2 sentences',
            'medium': '1 paragraph (3-5 sentences)',
            'long': '2-3 paragraphs'
        }

        return f"""Summarize the following content.

Content:
{content[:5000]}

Summary type: {summary_type}
Target length: {length_guidance.get(target_length, 'medium')}

Provide summary as JSON:
{{
  "summary": "The concise summary",
  "key_points": ["point 1", "point 2", "point 3"],
  "word_count": 150
}}
"""

    def validate_response(self, response: str) -> bool:
        try:
            data = json.loads(response.strip().strip('```json').strip('```'))
            return 'summary' in data
        except:
            return False

    async def do_continuous_work(self):
        pass


class ContextGathererBot(BaseBot):
    """
    Gathers contextual information from knowledge base
    Prepares data that main agents will need
    """

    async def build_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        gather_type = task.get('type', 'general')
        target = task.get('target', '')

        if gather_type == 'character_references':
            return f"""Gather all references to character: {target}

Search the knowledge base and compile:
{{
  "character": "{target}",
  "total_mentions": 0,
  "first_appearance": "Story X, Scene Y",
  "key_quotes": ["quote 1", "quote 2"],
  "relationships": {{}},
  "character_development": "How they change over time"
}}
"""

        elif gather_type == 'continuity_check':
            return f"""Check story continuity for: {target}

Verify:
{{
  "element": "{target}",
  "consistency": true/false,
  "issues_found": [],
  "notes": "Any continuity problems"
}}
"""

        else:
            return f"""Gather context for: {target}

Compile relevant information from knowledge base.
"""

    def validate_response(self, response: str) -> bool:
        return len(response) > 20

    async def do_continuous_work(self):
        pass


class DataExtractorBot(BaseBot):
    """
    Extracts structured data from unstructured content
    Useful for pulling lists, catalogs, inventories
    """

    async def build_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        content = task.get('content', '')
        extract_type = task.get('extract_type', 'list')

        if extract_type == 'character_list':
            return f"""Extract all character names from this content.

Content:
{content[:4000]}

Provide as JSON:
{{
  "characters": [
    {{
      "name": "Full name",
      "role": "main/supporting/minor",
      "first_mention": "Where they first appear"
    }}
  ]
}}
"""

        elif extract_type == 'dialogue':
            return f"""Extract all dialogue from this content.

Content:
{content[:4000]}

Provide as JSON:
{{
  "dialogue": [
    {{
      "character": "Speaker name",
      "line": "What they said",
      "scene": "Scene number or context"
    }}
  ]
}}
"""

        elif extract_type == 'action_items':
            return f"""Extract all action items and tasks from this content.

Content:
{content[:4000]}

Provide as JSON:
{{
  "actions": [
    {{
      "action": "What needs to happen",
      "priority": "high/medium/low",
      "dependencies": []
    }}
  ]
}}
"""

        else:
            return f"""Extract structured data of type '{extract_type}' from this content.

Content:
{content[:4000]}

Provide as JSON with appropriate structure.
"""

    def validate_response(self, response: str) -> bool:
        try:
            json.loads(response.strip().strip('```json').strip('```'))
            return True
        except:
            return False

    async def do_continuous_work(self):
        pass
