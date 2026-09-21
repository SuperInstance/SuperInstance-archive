# src/lora/lora_manager.py

import json
import os
from typing import Dict, Any, List


class LoRAManager:
    """Manages user and project-specific LoRA adapters"""

    def __init__(self, lora_dir: str = "data/loras"):
        self.lora_dir = lora_dir
        os.makedirs(f"{lora_dir}/user_preferences", exist_ok=True)
        os.makedirs(f"{lora_dir}/project_specific", exist_ok=True)

    async def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user-specific context and preferences"""
        user_file = f"{self.lora_dir}/user_preferences/{user_id}.json"

        if os.path.exists(user_file):
            with open(user_file, 'r') as f:
                return json.load(f)

        # Default context for new users
        return {
            "content_preferences": "high quality, detailed",
            "preferred_style": "professional",
            "known_projects": [],
            "expertise_level": "intermediate"
        }

    async def update_user_context(self, user_id: str, updates: Dict[str, Any]):
        """Update user context based on interactions"""
        current = await self.get_user_context(user_id)
        current.update(updates)

        user_file = f"{self.lora_dir}/user_preferences/{user_id}.json"
        with open(user_file, 'w') as f:
            json.dump(current, f, indent=2)

    async def get_project_adapter(self, project_id: str) -> str:
        """Get path to project-specific LoRA adapter"""
        adapter_path = f"{self.lora_dir}/project_specific/{project_id}"
        if os.path.exists(adapter_path):
            return adapter_path
        return None

    async def train_project_adapter(self, project_id: str, training_data: List[Dict]):
        """Train a project-specific LoRA adapter"""
        # This would use PEFT library to fine-tune
        # Simplified for now - stores training data for future implementation
        training_file = f"{self.lora_dir}/project_specific/{project_id}_training.json"
        with open(training_file, 'w') as f:
            json.dump(training_data, f, indent=2)
        print(f"✓ Training data saved for project {project_id}")
