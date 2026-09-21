# src/bots/content_bots.py

from .base_bot import BaseBot, BotConfig
import asyncio
import json
import time
import os
import glob
from typing import Dict, Any


class ScriptWriterBot(BaseBot):
    """Adapts story files to video or podcast scripts"""

    async def build_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        story_content = task.get('story_content', '')
        target_format = task.get('format', 'youtube_episode')
        target_duration = task.get('duration_minutes', 28)

        return f"""You are a script writer specializing in adapting stories for {target_format}.

Target Format: {target_format}
Target Duration: {target_duration} minutes
Visual Style: {context.get('visual_style', 'anime/Studio Ghibli')}

Story to Adapt:
{story_content[:5000]}  # Limit context

Your Task:
1. Break the story into clear scenes with visual descriptions
2. Include character actions, emotions, and dialogue
3. Add scene transitions and pacing notes
4. Maintain story integrity while optimizing for {target_format}

Format your response as structured JSON:
{{
  "title": "Episode title",
  "scenes": [
    {{
      "number": 1,
      "location": "...",
      "time": "...",
      "description": "Visual description of the scene",
      "action": "What happens",
      "dialogue": [
        {{"character": "Name", "line": "...", "emotion": "..."}},
        ...
      ],
      "duration_estimate": "2 minutes",
      "notes": "Pacing or technical notes"
    }},
    ...
  ],
  "total_scenes": 10,
  "estimated_runtime": "{target_duration} minutes"
}}
"""

    def validate_response(self, response: str) -> bool:
        try:
            data = json.loads(response.strip().strip('```json').strip('```'))
            return "scenes" in data and len(data.get("scenes", [])) > 0
        except:
            return False

    async def do_continuous_work(self):
        pass  # Not always-running


class ImagePrompterBot(BaseBot):
    """Generates detailed image prompts for AI image generation"""

    async def build_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        scene_description = task.get('scene_description', '')
        character_name = task.get('character', '')
        prompt_type = task.get('type', 'character')  # character, background, scene

        return f"""You are an expert at creating detailed image generation prompts.

Visual Style: {context.get('visual_style', 'anime, Studio Ghibli quality')}
Prompt Type: {prompt_type}

Scene/Character Description:
{scene_description}

Character Reference (if applicable): {character_name}
- Casey Chen: 16-year-old boy, messy dark hair, curious expression, casual tech wear
- Anna: Young dancer, perfect posture, intense eyes, dance attire
- Finn: Sailor, weather-worn face, confident stance, maritime clothing
- SuperInstance: Ethereal AI entity, holographic, gentle presence

Create a detailed prompt for Stable Diffusion XL / DALL-E 3:
1. Include style keywords (anime, painterly, soft lighting, etc.)
2. Describe composition, lighting, mood
3. Specify character details and expressions
4. Add technical parameters (8K, highly detailed, cinematic, etc.)

Provide as JSON:
{{
  "prompt": "Main detailed prompt for image generation",
  "negative_prompt": "Things to avoid (blurry, low quality, etc.)",
  "style_tags": ["anime", "ghibli", "painterly"],
  "technical_params": {{
    "aspect_ratio": "16:9",
    "quality": "high",
    "guidance": 7.5
  }}
}}
"""

    def validate_response(self, response: str) -> bool:
        try:
            data = json.loads(response.strip().strip('```json').strip('```'))
            return "prompt" in data and len(data.get("prompt", "")) > 20
        except:
            return False

    async def do_continuous_work(self):
        pass


class DialogueFormatterBot(BaseBot):
    """Formats dialogue for voice synthesis with emotion tags"""

    async def build_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        dialogue_lines = task.get('dialogue', [])

        return f"""You are a voice synthesis specialist. Format dialogue for ElevenLabs voice synthesis.

Audio Style: {context.get('audio_style', 'natural, expressive')}

Dialogue to Format:
{json.dumps(dialogue_lines, indent=2)}

Character Voice Profiles:
- Casey Chen: Teen male, curious, slightly nervous
- Anna: Young female, confident, precise
- Finn: Adult male, calm, authoritative
- Michele: Adult, warm, knowing
- SuperInstance: Androgynous, gentle, ethereal

Format each line with:
1. Character name
2. Voice settings (pitch, speed, emotion)
3. Formatted text with SSML tags for emphasis, pauses
4. Emotion indicators for ElevenLabs

Provide as JSON:
{{
  "formatted_dialogue": [
    {{
      "character": "Casey",
      "voice_id": "teen_male_curious",
      "text": "Wait, what do you mean?",
      "ssml": "<speak>Wait<break time='500ms'/> what do you mean?</speak>",
      "emotion": "curious",
      "settings": {{"pitch": 1.0, "speed": 1.0, "stability": 0.5}}
    }},
    ...
  ],
  "total_lines": 10,
  "estimated_duration": "2 minutes 30 seconds"
}}
"""

    def validate_response(self, response: str) -> bool:
        try:
            data = json.loads(response.strip().strip('```json').strip('```'))
            return "formatted_dialogue" in data
        except:
            return False

    async def do_continuous_work(self):
        pass


class StoryIndexerBot(BaseBot):
    """Always-running bot that maintains searchable index of all stories"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.indexed_stories = set()
        self.last_index_time = 0

    async def do_continuous_work(self):
        """Continuously index story files"""
        # Only reindex every 5 minutes
        if time.time() - self.last_index_time < 300:
            return

        story_path = "/home/activeloguser"
        story_files = glob.glob(f"{story_path}/Story_*_v3.md")

        for story_file in story_files:
            if story_file not in self.indexed_stories:
                try:
                    # Read story
                    with open(story_file, 'r') as f:
                        content = f.read()

                    # Extract metadata
                    filename = os.path.basename(story_file)
                    parts = filename.replace('.md', '').split('_')

                    metadata = {
                        "title": ' '.join(parts[2:-1]) if len(parts) > 3 else filename,
                        "version": parts[-1] if len(parts) > 0 else "unknown",
                        "path": story_file,
                        "word_count": len(content.split())
                    }

                    # Store in knowledge base
                    await self.knowledge_base.index_story(story_file, content, metadata)

                    self.indexed_stories.add(story_file)
                    print(f"📚 Indexed: {metadata['title']}")

                    await asyncio.sleep(1)  # Rate limit

                except Exception as e:
                    print(f"❌ Error indexing {story_file}: {e}")

        self.last_index_time = time.time()
        print(f"✓ Story index updated: {len(self.indexed_stories)} stories")

    async def build_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        pass  # This bot doesn't handle queued tasks


class AssetMonitorBot(BaseBot):
    """Always-running bot that tracks generated assets"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.asset_counts = {
            "characters": 0,
            "backgrounds": 0,
            "audio": 0,
            "video": 0
        }

    async def do_continuous_work(self):
        """Monitor asset directories"""
        asset_paths = {
            "characters": "data/assets/characters",
            "backgrounds": "data/assets/backgrounds",
            "audio": "data/assets/audio",
            "video": "data/assets/video"
        }

        for asset_type, path in asset_paths.items():
            if os.path.exists(path):
                count = len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
                if count != self.asset_counts[asset_type]:
                    print(f"📁 {asset_type.capitalize()}: {count} assets")
                    self.asset_counts[asset_type] = count

                    # Alert if low on assets
                    if count < 5:
                        await self.message_bus.send_alert({
                            'type': 'low_asset_count',
                            'asset_type': asset_type,
                            'count': count
                        })

    async def build_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        pass


class MetadataGeneratorBot(BaseBot):
    """Generates YouTube titles, descriptions, podcast metadata"""

    async def build_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        content_type = task.get('content_type', 'youtube')
        episode_summary = task.get('summary', '')
        episode_number = task.get('episode_number', 1)

        return f"""You are a content marketing specialist. Create metadata for {content_type}.

Episode Number: {episode_number}
Series: Loopless/SuperInstance
Episode Summary:
{episode_summary}

Platform: {content_type}
Target Audience: Fans of philosophical sci-fi, anime, Studio Ghibli

Create:
1. Compelling title (SEO-optimized, intriguing)
2. Full description with timestamps
3. Tags/keywords
4. Thumbnail description
5. Social media snippet

Provide as JSON:
{{
  "title": "Episode {episode_number}: [Compelling Title]",
  "description": "Full episode description with timestamps and links",
  "tags": ["scifi", "anime", "philosophy", ...],
  "thumbnail_description": "Visual description for thumbnail creation",
  "social_snippet": "Tweet-length teaser (280 chars)",
  "seo_keywords": ["keyword1", "keyword2", ...]
}}
"""

    def validate_response(self, response: str) -> bool:
        try:
            data = json.loads(response.strip().strip('```json').strip('```'))
            return "title" in data and "description" in data
        except:
            return False

    async def do_continuous_work(self):
        pass


class QAContentBot(BaseBot):
    """Quality assurance - checks consistency, pacing, story accuracy"""

    async def build_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        content_to_review = task.get('content', '')
        original_story = task.get('original_story', '')

        return f"""You are a quality assurance specialist for content production.

Original Story:
{original_story[:3000]}

Adapted Content to Review:
{content_to_review[:3000]}

Check for:
1. Story accuracy - does it faithfully represent the original?
2. Character consistency - are characters true to their descriptions?
3. Pacing - is it appropriate for the target duration?
4. Continuity - are there any logical gaps or contradictions?
5. Technical quality - formatting, completeness

Provide detailed review as JSON:
{{
  "overall_score": 8.5,
  "story_accuracy": {{"score": 9, "notes": "..."}},
  "character_consistency": {{"score": 8, "notes": "..."}},
  "pacing": {{"score": 8, "notes": "..."}},
  "continuity": {{"score": 9, "notes": "..."}},
  "issues_found": ["issue 1", "issue 2"],
  "recommendations": ["recommendation 1", "recommendation 2"],
  "approved": true
}}
"""

    def validate_response(self, response: str) -> bool:
        try:
            data = json.loads(response.strip().strip('```json').strip('```'))
            return "overall_score" in data and "approved" in data
        except:
            return False

    async def do_continuous_work(self):
        pass
