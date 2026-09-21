"""
State Manager
Manages conversation state and system status
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from uuid import uuid4
import json
import os


@dataclass
class Interaction:
    """Single user-assistant interaction"""
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    user_input: str = ""
    response: str = ""
    model: str = ""
    cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    tools_used: List[str] = field(default_factory=list)


class StateManager:
    """
    Manages system state and interaction history
    """

    def __init__(self, save_conversations: bool = True, log_dir: str = "./logs"):
        """
        Initialize state manager

        Args:
            save_conversations: Whether to save conversations to disk
            log_dir: Directory for conversation logs
        """
        self.save_conversations = save_conversations
        self.log_dir = log_dir
        self.session_start = datetime.now()

        # Interaction history
        self.interactions: List[Interaction] = []

        # System status
        self.loaded_models: List[str] = []
        self.gpu_status: Optional[Dict] = None

        # Create log directory
        if save_conversations:
            os.makedirs(log_dir, exist_ok=True)

    def record_interaction(
        self,
        user_input: str,
        response: str,
        model: str,
        cost: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        tools_used: Optional[List[str]] = None
    ):
        """
        Record an interaction

        Args:
            user_input: User's input
            response: Model's response
            model: Model name
            cost: Cost in USD
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            tools_used: List of tools used
        """
        interaction = Interaction(
            user_input=user_input,
            response=response,
            model=model,
            cost=cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tools_used=tools_used or []
        )

        self.interactions.append(interaction)

        # Save to disk if enabled
        if self.save_conversations:
            self._save_interaction(interaction)

    def _save_interaction(self, interaction: Interaction):
        """Save interaction to log file"""
        # Create daily log file
        log_file = os.path.join(
            self.log_dir,
            f"autocoder_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        )

        # Append interaction as JSON line
        with open(log_file, 'a') as f:
            data = {
                'id': interaction.id,
                'timestamp': interaction.timestamp.isoformat(),
                'user_input': interaction.user_input,
                'response': interaction.response,
                'model': interaction.model,
                'cost': interaction.cost,
                'input_tokens': interaction.input_tokens,
                'output_tokens': interaction.output_tokens,
                'tools_used': interaction.tools_used
            }
            f.write(json.dumps(data) + '\n')

    def get_recent_interactions(self, count: int = 10) -> List[Interaction]:
        """Get recent interactions"""
        return self.interactions[-count:]

    def get_conversation_context(self, max_tokens: int = 10000) -> List[Dict[str, str]]:
        """
        Get conversation context for model

        Args:
            max_tokens: Maximum tokens to include

        Returns:
            List of message dicts
        """
        messages = []
        token_count = 0

        # Go backwards through interactions
        for interaction in reversed(self.interactions):
            # Estimate tokens (rough: 1 token ≈ 4 chars)
            interaction_tokens = (len(interaction.user_input) + len(interaction.response)) // 4

            if token_count + interaction_tokens > max_tokens:
                break

            # Prepend (since we're going backwards)
            messages.insert(0, {"role": "assistant", "content": interaction.response})
            messages.insert(0, {"role": "user", "content": interaction.user_input})

            token_count += interaction_tokens

        return messages

    def update_gpu_status(self, status: Dict):
        """Update GPU status"""
        self.gpu_status = {
            **status,
            'last_updated': datetime.now()
        }

    def update_loaded_models(self, models: List[str]):
        """Update list of loaded models"""
        self.loaded_models = models

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get current system status

        Returns:
            Dict with system information
        """
        uptime = datetime.now() - self.session_start
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        status = {
            'uptime': f"{hours}h {minutes}m {seconds}s",
            'tasks_completed': len(self.interactions),
            'loaded_models': self.loaded_models,
            'session_start': self.session_start.isoformat()
        }

        # Add GPU status if available
        if self.gpu_status:
            status['gpu'] = self.gpu_status

        return status

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get usage statistics

        Returns:
            Dict with stats
        """
        if not self.interactions:
            return {
                'total_interactions': 0,
                'total_cost': 0.0,
                'avg_cost': 0.0,
                'models_used': {},
                'total_tokens': 0
            }

        # Models used
        models_used = {}
        for interaction in self.interactions:
            models_used[interaction.model] = models_used.get(interaction.model, 0) + 1

        # Costs and tokens
        total_cost = sum(i.cost for i in self.interactions)
        total_tokens = sum(i.input_tokens + i.output_tokens for i in self.interactions)

        return {
            'total_interactions': len(self.interactions),
            'total_cost': total_cost,
            'avg_cost': total_cost / len(self.interactions),
            'models_used': models_used,
            'total_tokens': total_tokens,
            'avg_tokens_per_interaction': total_tokens / len(self.interactions)
        }

    def clear_history(self):
        """Clear interaction history (keeps logs on disk)"""
        self.interactions = []

    def export_session(self, filepath: str):
        """
        Export session to JSON file

        Args:
            filepath: Output file path
        """
        data = {
            'session_start': self.session_start.isoformat(),
            'session_end': datetime.now().isoformat(),
            'statistics': self.get_statistics(),
            'interactions': [
                {
                    'id': i.id,
                    'timestamp': i.timestamp.isoformat(),
                    'user_input': i.user_input,
                    'response': i.response,
                    'model': i.model,
                    'cost': i.cost,
                    'tokens': {
                        'input': i.input_tokens,
                        'output': i.output_tokens
                    },
                    'tools_used': i.tools_used
                }
                for i in self.interactions
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
