"""
Configuration Loader
Loads and validates configuration from YAML files
"""

import yaml
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Configuration for a single model"""
    name: str
    enabled: bool = True
    cost_per_1m_input: float = 0.0
    cost_per_1m_output: float = 0.0
    context_window: int = 32768
    supports_tools: bool = True
    vram_mb: Optional[int] = None


@dataclass
class HardwareConfig:
    """Hardware configuration"""
    gpu_vram_mb: int
    gpu_max_temp: int = 80
    cpu_cores: int = 12
    ram_gb: int = 32
    is_laptop: bool = True


@dataclass
class Config:
    """Complete application configuration"""
    hardware: HardwareConfig
    models: Dict[str, ModelConfig]
    routing_strategy: str = "hybrid"
    daily_budget: float = 5.0
    monthly_budget: float = 150.0
    thermal_enabled: bool = True
    cache_enabled: bool = True
    log_level: str = "INFO"
    save_conversations: bool = True


class ConfigLoader:
    """Loads configuration from YAML files and environment"""

    @staticmethod
    def load(config_path: str = "config/proart_px13.yaml") -> Config:
        """
        Load configuration from file

        Args:
            config_path: Path to YAML config file

        Returns:
            Config object
        """
        # Load YAML
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)

        # Parse hardware config
        hw_data = data.get('hardware', {})
        hardware = HardwareConfig(
            gpu_vram_mb=hw_data.get('gpu', {}).get('vram_mb', 6141),
            gpu_max_temp=hw_data.get('gpu', {}).get('max_temp_celsius', 80),
            cpu_cores=hw_data.get('cpu', {}).get('cores', 12),
            ram_gb=hw_data.get('ram_gb', 32),
            is_laptop=hw_data.get('is_laptop', True)
        )

        # Parse model configs
        models = {}

        # Ollama (local) models
        if 'providers' in data and 'ollama' in data['providers']:
            ollama = data['providers']['ollama']
            if ollama.get('enabled', True):
                for model_key, model_data in ollama.get('models', {}).items():
                    models[f"ollama_{model_key}"] = ModelConfig(
                        name=model_data.get('name', 'qwen2.5-coder:7b'),
                        enabled=True,
                        cost_per_1m_input=0.0,  # Local is free
                        cost_per_1m_output=0.0,
                        context_window=model_data.get('context_window', 32768),
                        supports_tools=True,
                        vram_mb=model_data.get('vram_mb')
                    )

        # Claude models
        if 'providers' in data and 'claude' in data['providers']:
            claude = data['providers']['claude']
            if claude.get('enabled', True):
                for model_key, model_data in claude.get('models', {}).items():
                    models[f"claude_{model_key}"] = ModelConfig(
                        name=model_data.get('name', 'claude-sonnet-4'),
                        enabled=True,
                        cost_per_1m_input=model_data.get('cost_input_per_1m', 3.0),
                        cost_per_1m_output=model_data.get('cost_output_per_1m', 15.0),
                        context_window=200000,
                        supports_tools=True
                    )

        # Budget configuration
        budget = data.get('budget', {})
        daily_budget = budget.get('daily_limit', 5.0)
        monthly_budget = budget.get('monthly_limit', 150.0)

        # Other settings
        routing = data.get('routing', {})
        thermal = data.get('thermal', {})
        cache = data.get('cache', {})
        logging = data.get('logging', {})

        return Config(
            hardware=hardware,
            models=models,
            routing_strategy=routing.get('strategy', 'hybrid'),
            daily_budget=daily_budget,
            monthly_budget=monthly_budget,
            thermal_enabled=thermal.get('enabled', True),
            cache_enabled=cache.get('enabled', True),
            log_level=logging.get('level', 'INFO'),
            save_conversations=logging.get('save_conversations', True)
        )

    @staticmethod
    def load_env() -> Dict[str, str]:
        """
        Load environment variables

        Returns:
            Dict of environment variables
        """
        env_vars = {}

        # Try to load from .env file
        env_file = '.env'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip().strip('"').strip("'")

        # Override with actual environment variables
        for key in ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'GOOGLE_API_KEY']:
            if key in os.environ:
                env_vars[key] = os.environ[key]

        return env_vars

    @staticmethod
    def validate_config(config: Config) -> bool:
        """
        Validate configuration

        Args:
            config: Config to validate

        Returns:
            True if valid

        Raises:
            ValueError if invalid
        """
        # Check at least one model is configured
        if not config.models:
            raise ValueError("No models configured")

        # Check budget limits
        if config.daily_budget <= 0:
            raise ValueError("Daily budget must be positive")

        if config.monthly_budget <= 0:
            raise ValueError("Monthly budget must be positive")

        # Check hardware
        if config.hardware.gpu_vram_mb <= 0:
            raise ValueError("GPU VRAM must be positive")

        return True
