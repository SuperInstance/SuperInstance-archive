"""
User Experience Profiles
Manages user experience levels and preferences
"""

import os
import json
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from pathlib import Path


class ExperienceLevel(Enum):
    """User experience level"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    PROFESSIONAL = "professional"
    CUSTOM = "custom"


@dataclass
class UserProfile:
    """User profile with preferences"""
    experience_level: ExperienceLevel
    show_hints: bool = True
    show_routing_details: bool = True
    show_cost_warnings: bool = True
    auto_decompose: bool = True
    confirm_expensive_tasks: bool = True
    verbose_errors: bool = True
    use_shortcuts: bool = False
    theme: str = "default"
    daily_budget_limit: float = 5.0
    preferred_models: Dict[str, str] = None

    def __post_init__(self):
        if self.preferred_models is None:
            self.preferred_models = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        d = asdict(self)
        d['experience_level'] = self.experience_level.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create from dictionary"""
        data['experience_level'] = ExperienceLevel(data['experience_level'])
        return cls(**data)


class ProfileManager:
    """Manages user profiles and preferences"""

    def __init__(self, config_dir: str = None):
        """
        Initialize profile manager

        Args:
            config_dir: Directory to store config (default: ~/.autocoder)
        """
        if config_dir is None:
            config_dir = os.path.expanduser("~/.autocoder")

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.profile_path = self.config_dir / "profile.json"
        self.profile: Optional[UserProfile] = None

    def load_profile(self) -> UserProfile:
        """Load user profile or create default"""
        if self.profile_path.exists():
            try:
                with open(self.profile_path, 'r') as f:
                    data = json.load(f)
                    self.profile = UserProfile.from_dict(data)
                    return self.profile
            except Exception as e:
                print(f"⚠️  Error loading profile: {e}")
                # Fall through to create default

        # Create default profile
        self.profile = self.create_default_profile()
        return self.profile

    def save_profile(self):
        """Save current profile"""
        if self.profile:
            with open(self.profile_path, 'w') as f:
                json.dump(self.profile.to_dict(), f, indent=2)

    def create_default_profile(self) -> UserProfile:
        """Create default beginner profile"""
        return UserProfile(
            experience_level=ExperienceLevel.BEGINNER,
            show_hints=True,
            show_routing_details=True,
            show_cost_warnings=True,
            auto_decompose=True,
            confirm_expensive_tasks=True,
            verbose_errors=True,
            use_shortcuts=False,
            theme="default",
            daily_budget_limit=5.0
        )

    def create_beginner_profile(self) -> UserProfile:
        """Create beginner-friendly profile"""
        return UserProfile(
            experience_level=ExperienceLevel.BEGINNER,
            show_hints=True,
            show_routing_details=True,
            show_cost_warnings=True,
            auto_decompose=True,
            confirm_expensive_tasks=True,
            verbose_errors=True,
            use_shortcuts=False,
            theme="default",
            daily_budget_limit=5.0
        )

    def create_intermediate_profile(self) -> UserProfile:
        """Create intermediate user profile"""
        return UserProfile(
            experience_level=ExperienceLevel.INTERMEDIATE,
            show_hints=False,  # Less hand-holding
            show_routing_details=True,
            show_cost_warnings=True,
            auto_decompose=True,
            confirm_expensive_tasks=False,  # Trust user more
            verbose_errors=True,
            use_shortcuts=True,  # Enable shortcuts
            theme="default",
            daily_budget_limit=10.0  # Higher budget
        )

    def create_professional_profile(self) -> UserProfile:
        """Create professional user profile"""
        return UserProfile(
            experience_level=ExperienceLevel.PROFESSIONAL,
            show_hints=False,  # No hints
            show_routing_details=False,  # Quiet mode
            show_cost_warnings=False,  # User knows what they're doing
            auto_decompose=True,
            confirm_expensive_tasks=False,
            verbose_errors=False,  # Concise errors
            use_shortcuts=True,
            theme="minimal",
            daily_budget_limit=50.0  # Much higher budget
        )

    def set_profile(self, level: ExperienceLevel):
        """Set profile by experience level"""
        if level == ExperienceLevel.BEGINNER:
            self.profile = self.create_beginner_profile()
        elif level == ExperienceLevel.INTERMEDIATE:
            self.profile = self.create_intermediate_profile()
        elif level == ExperienceLevel.PROFESSIONAL:
            self.profile = self.create_professional_profile()

        self.save_profile()

    def update_preference(self, key: str, value: Any):
        """Update a single preference"""
        if self.profile and hasattr(self.profile, key):
            setattr(self.profile, key, value)
            self.save_profile()

    def is_first_run(self) -> bool:
        """Check if this is the first run"""
        return not self.profile_path.exists()

    def mark_tutorial_completed(self):
        """Mark that user has completed tutorial"""
        tutorial_flag = self.config_dir / ".tutorial_completed"
        tutorial_flag.touch()

    def has_completed_tutorial(self) -> bool:
        """Check if user has completed tutorial"""
        tutorial_flag = self.config_dir / ".tutorial_completed"
        return tutorial_flag.exists()


def get_tips_for_level(level: ExperienceLevel) -> list[str]:
    """Get helpful tips based on experience level"""

    if level == ExperienceLevel.BEGINNER:
        return [
            "💡 Tip: Type ':help' to see all available commands",
            "💡 Tip: Use '@local' to force local GPU (free but slower)",
            "💡 Tip: Use '@claude' to force Claude (fast but costs money)",
            "💡 Tip: Complex tasks are automatically broken down to save costs",
            "💡 Tip: Type ':cost' to see how much you've spent",
            "💡 Tip: Type ':examples' to see common usage examples",
            "💡 Tip: The system automatically chooses the best model for each task",
            "💡 Tip: Green text means the task was handled locally for FREE"
        ]
    elif level == ExperienceLevel.INTERMEDIATE:
        return [
            "💡 Tip: Use Ctrl+R to search command history",
            "💡 Tip: ':context' shows your conversation context and subtasks",
            "💡 Tip: Complex tasks decompose automatically - use '@model' to override",
            "💡 Tip: Set daily budget with ':cost limit <amount>'",
            "💡 Tip: Check GPU status with ':status' before heavy local work"
        ]
    elif level == ExperienceLevel.PROFESSIONAL:
        return [
            "💡 Shortcuts: :h (help), :m (models), :c (cost), :s (status), :q (quit)",
            "💡 Disable decomposition per task with '@' override",
            "💡 Contexts persist in ~/.autocoder/contexts/ for debugging",
            "💡 Profile settings: ~/.autocoder/profile.json"
        ]

    return []


def get_welcome_message(level: ExperienceLevel) -> str:
    """Get welcome message based on experience level"""

    if level == ExperienceLevel.BEGINNER:
        return """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                Welcome to AutoCoder! 🎉                      ║
║                                                              ║
║  A smart coding assistant that saves you money by using     ║
║  your local GPU for simple tasks and cloud AI only when     ║
║  needed for complex work.                                   ║
║                                                              ║
║  🎓 BEGINNER MODE ACTIVE                                     ║
║  - Helpful hints and tips enabled                           ║
║  - Detailed explanations provided                           ║
║  - Cost warnings before expensive operations                ║
║                                                              ║
║  Type ':help' to get started or just ask a question!        ║
║  Example: "Write a Python function to sort a list"          ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    elif level == ExperienceLevel.INTERMEDIATE:
        return """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                  AutoCoder v0.2.0                            ║
║            Multi-Model Coding Assistant                      ║
║                                                              ║
║  ⚡ INTERMEDIATE MODE                                        ║
║  - Shortcuts enabled                                         ║
║  - Auto-decomposition active                                 ║
║  - Daily budget: $10.00                                      ║
║                                                              ║
║  Quick start: ':help' | Examples: ':examples'               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    elif level == ExperienceLevel.PROFESSIONAL:
        return """
╔════════════════════════════════════════════════════════╗
║                                                        ║
║              AutoCoder v0.2.0 - Pro Mode               ║
║                                                        ║
║  Decomposition: ON | Budget: $50/day | GPU: Ready     ║
║  :h :m :c :s :ctx :q | @local @claude @haiku          ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
"""

    return ""


def get_error_suggestion(error_type: str, level: ExperienceLevel) -> str:
    """Get helpful error suggestions based on experience level"""

    suggestions = {
        'no_api_key': {
            ExperienceLevel.BEGINNER: """
❌ No API key found for Claude.

To use cloud models, you need an API key from Anthropic:
1. Go to https://console.anthropic.com
2. Create an account (free trial available!)
3. Get your API key
4. Run: export ANTHROPIC_API_KEY='your-key-here'

OR you can use local models only (FREE but slower):
- They'll be used automatically if no API key is set
- Perfect for practice and simple tasks!

Type ':help setup' for more details.
""",
            ExperienceLevel.INTERMEDIATE: """
❌ ANTHROPIC_API_KEY not set

Set your API key:
  export ANTHROPIC_API_KEY='sk-ant-...'

Or add to ~/.bashrc for persistence.
You can still use local models without an API key.
""",
            ExperienceLevel.PROFESSIONAL: """
❌ ANTHROPIC_API_KEY not set

  export ANTHROPIC_API_KEY='sk-ant-...'

Local models still available.
"""
        },
        'ollama_not_found': {
            ExperienceLevel.BEGINNER: """
❌ Local model (Ollama) not found.

Local models run on your GPU for FREE! To set them up:
1. Run: sudo bash install_ollama.sh
2. Wait for installation (2-3 minutes)
3. Run: bash setup_complete.sh (downloads model, ~5GB)
4. Restart AutoCoder

Don't have Ollama? You can still use cloud models by setting an API key.

Type ':help setup' for more details.
""",
            ExperienceLevel.INTERMEDIATE: """
❌ Ollama not available

Install: sudo bash install_ollama.sh
Then: bash setup_complete.sh

Cloud models still work if API key is set.
""",
            ExperienceLevel.PROFESSIONAL: """
❌ Ollama not found

  sudo bash install_ollama.sh && bash setup_complete.sh
"""
        },
        'gpu_overheating': {
            ExperienceLevel.BEGINNER: """
⚠️  Your GPU is getting hot! 🔥

To protect your laptop, AutoCoder is switching to cloud models temporarily.
This is normal during intensive local inference.

What's happening:
- Your GPU reached 80°C (the safety limit)
- AutoCoder will wait 60 seconds for it to cool down
- Then you can use local models again

Tips to keep things cool:
- Make sure your laptop has good ventilation
- Use a cooling pad if available
- Consider using cloud models for heavy tasks (@claude)
""",
            ExperienceLevel.INTERMEDIATE: """
⚠️  GPU thermal limit reached (80°C)

Cooldown period active. Routing to cloud temporarily.
Tips: Check ventilation, consider cooling pad.
""",
            ExperienceLevel.PROFESSIONAL: """
⚠️  GPU throttling (80°C) - routing to cloud
"""
        }
    }

    error_suggestions = suggestions.get(error_type, {})
    return error_suggestions.get(level, "❌ An error occurred. Check logs for details.")
