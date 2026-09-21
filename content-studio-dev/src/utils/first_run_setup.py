# src/utils/first_run_setup.py
"""
First-run setup wizard for API keys and configuration
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional


class FirstRunSetup:
    """Interactive setup wizard for first-time users"""

    def __init__(self, env_path: str = ".env"):
        self.env_path = Path(env_path)
        self.config = {}

    def run(self) -> bool:
        """
        Run the setup wizard

        Returns:
            True if setup completed, False if skipped
        """
        print("\n" + "="*60)
        print("🚀 LOOPLESS CONTENT STUDIO - FIRST RUN SETUP")
        print("="*60 + "\n")

        # Check if .env already exists and has keys
        if self._check_existing_config():
            print("✓ Existing configuration found!")
            response = input("\nDo you want to reconfigure? (y/N): ").lower()
            if response != 'y':
                print("\nUsing existing configuration.")
                return True

        print("\nWelcome! Let's set up your API keys for the multi-agent system.")
        print("\nYou'll need API keys from providers to run the system.")
        print("Don't worry - you can skip providers and add them later!")
        print("\n" + "-"*60 + "\n")

        # Gather API keys
        self._setup_anthropic()
        self._setup_openai()
        self._setup_groq()
        self._setup_together()

        # Ask about optional keys
        print("\n" + "-"*60)
        print("OPTIONAL: Additional Services")
        print("-"*60 + "\n")

        if self._ask_yes_no("Set up ElevenLabs (voice synthesis)?", default=False):
            self._setup_elevenlabs()

        # Save configuration
        self._save_config()

        # Summary
        self._print_summary()

        return True

    def _check_existing_config(self) -> bool:
        """Check if configuration already exists"""
        if not self.env_path.exists():
            return False

        # Read existing .env
        with open(self.env_path, 'r') as f:
            content = f.read()

        # Check if any API keys are set
        has_keys = any([
            'ANTHROPIC_API_KEY=' in content and 'your-' not in content,
            'OPENAI_API_KEY=' in content and 'your-' not in content,
            'GROQ_API_KEY=' in content and 'your-' not in content
        ])

        return has_keys

    def _setup_anthropic(self):
        """Setup Anthropic Claude API"""
        print("🤖 ANTHROPIC CLAUDE")
        print("   Used for: Orchestrator (project planning) and Foreman (task management)")
        print("   Cost: ~$3-15 per 1M tokens (Sonnet)")
        print("   Get key: https://console.anthropic.com/\n")

        key = self._get_api_key("Anthropic", required=True)
        if key:
            self.config['ANTHROPIC_API_KEY'] = key

    def _setup_openai(self):
        """Setup OpenAI API"""
        print("\n🧠 OPENAI")
        print("   Used for: Content agents (writing, formatting)")
        print("   Cost: ~$0.15-0.60 per 1M tokens (GPT-4o mini)")
        print("   Get key: https://platform.openai.com/api-keys\n")

        key = self._get_api_key("OpenAI", required=False)
        if key:
            self.config['OPENAI_API_KEY'] = key

    def _setup_groq(self):
        """Setup Groq API"""
        print("\n⚡ GROQ")
        print("   Used for: Background research (FREE tier available!)")
        print("   Cost: FREE for Llama models (with rate limits)")
        print("   Get key: https://console.groq.com/\n")
        print("   ⭐ HIGHLY RECOMMENDED - It's FREE!\n")

        key = self._get_api_key("Groq", required=False)
        if key:
            self.config['GROQ_API_KEY'] = key

    def _setup_together(self):
        """Setup Together AI"""
        print("\n🤝 TOGETHER AI")
        print("   Used for: Alternative content generation")
        print("   Cost: ~$0.20 per 1M tokens")
        print("   Get key: https://api.together.xyz/\n")

        key = self._get_api_key("Together AI", required=False)
        if key:
            self.config['TOGETHER_API_KEY'] = key

    def _setup_elevenlabs(self):
        """Setup ElevenLabs voice synthesis"""
        print("\n🎤 ELEVENLABS")
        print("   Used for: Voice synthesis (optional)")
        print("   Cost: Free tier available")
        print("   Get key: https://elevenlabs.io/\n")

        key = self._get_api_key("ElevenLabs", required=False)
        if key:
            self.config['ELEVENLABS_API_KEY'] = key

    def _get_api_key(self, provider: str, required: bool = False) -> Optional[str]:
        """
        Prompt user for API key

        Args:
            provider: Provider name
            required: Whether this key is required

        Returns:
            API key or None
        """
        if required:
            prompt = f"Enter your {provider} API key (REQUIRED): "
        else:
            prompt = f"Enter your {provider} API key (press Enter to skip): "

        while True:
            key = input(prompt).strip()

            if not key:
                if required:
                    print("   ⚠️ This key is required. Please provide it.")
                    continue
                else:
                    print(f"   ⏭️ Skipping {provider}")
                    return None

            # Basic validation
            if len(key) < 10:
                print("   ⚠️ That doesn't look like a valid API key. Please check and try again.")
                continue

            # Confirm
            masked = key[:8] + "..." + key[-4:]
            print(f"   ✓ Saved: {masked}")
            return key

    def _ask_yes_no(self, question: str, default: bool = False) -> bool:
        """Ask a yes/no question"""
        default_str = "Y/n" if default else "y/N"
        response = input(f"{question} ({default_str}): ").lower().strip()

        if not response:
            return default

        return response[0] == 'y'

    def _save_config(self):
        """Save configuration to .env file"""
        print("\n" + "-"*60)
        print("💾 Saving configuration...")

        # Read existing .env as template
        if self.env_path.exists():
            with open(self.env_path, 'r') as f:
                lines = f.readlines()
        else:
            # Create from scratch
            lines = [
                "# Loopless Content Studio - API Configuration\n",
                "# Generated by first-run setup\n",
                "\n",
                "# Required\n",
                "ANTHROPIC_API_KEY=\n",
                "\n",
                "# Optional (but recommended)\n",
                "OPENAI_API_KEY=\n",
                "GROQ_API_KEY=\n",
                "TOGETHER_API_KEY=\n",
                "\n",
                "# Optional services\n",
                "ELEVENLABS_API_KEY=\n",
                "\n"
            ]

        # Update lines with new values
        updated_lines = []
        for line in lines:
            key_found = False
            for config_key, config_value in self.config.items():
                if line.startswith(f"{config_key}="):
                    updated_lines.append(f"{config_key}={config_value}\n")
                    key_found = True
                    break

            if not key_found:
                updated_lines.append(line)

        # Write back
        with open(self.env_path, 'w') as f:
            f.writelines(updated_lines)

        print(f"✓ Configuration saved to: {self.env_path}")

    def _print_summary(self):
        """Print setup summary"""
        print("\n" + "="*60)
        print("✅ SETUP COMPLETE!")
        print("="*60 + "\n")

        print("Configuration Summary:")
        print("-" * 40)

        providers_configured = len(self.config)
        print(f"✓ {providers_configured} API provider(s) configured")

        for key in self.config.keys():
            provider = key.replace('_API_KEY', '').replace('_', ' ').title()
            print(f"  • {provider}")

        print("\nNext Steps:")
        print("-" * 40)
        print("1. Start the system with: ./start.sh")
        print("2. Or run manually with: python -m src.orchestrator.main")
        print("3. Access the API at: http://localhost:8000")
        print("\nTip: You can reconfigure anytime by running this script again")
        print("     or by editing the .env file directly.\n")


def main():
    """Run first-run setup"""
    setup = FirstRunSetup()

    try:
        setup.run()
    except KeyboardInterrupt:
        print("\n\n⚠️ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
