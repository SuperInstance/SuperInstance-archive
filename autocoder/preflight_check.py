#!/usr/bin/env python3
"""
Pre-flight Check for AutoCoder
Verifies all prerequisites before running the application
"""

import os
import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Check Python version >= 3.8"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} (requires >= 3.8)")
        return False


def check_gpu():
    """Check if NVIDIA GPU is accessible"""
    try:
        # Try nvidia-smi
        nvidia_smi_paths = [
            "/usr/lib/wsl/lib/nvidia-smi",
            "/usr/bin/nvidia-smi",
            "nvidia-smi"
        ]

        for path in nvidia_smi_paths:
            try:
                result = subprocess.run(
                    [path, "--query-gpu=name,memory.total", "--format=csv,noheader"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )

                if result.returncode == 0:
                    gpu_info = result.stdout.strip()
                    print(f"✓ GPU: {gpu_info}")
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue

        print("⚠️  GPU not detected (local inference unavailable)")
        return False

    except Exception as e:
        print(f"⚠️  GPU check failed: {e}")
        return False


def check_ollama():
    """Check if Ollama is installed and running"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            # Check if qwen model is available
            if "qwen2.5-coder:7b-instruct-q4_K_M" in result.stdout:
                print("✓ Ollama installed with qwen2.5-coder:7b model")
                return True
            else:
                print("⚠️  Ollama installed but qwen2.5-coder:7b model not found")
                print("   Run: ollama pull qwen2.5-coder:7b-instruct-q4_K_M")
                return False
        else:
            print("❌ Ollama not responding")
            print("   Run: sudo bash install_ollama.sh")
            return False

    except FileNotFoundError:
        print("❌ Ollama not installed")
        print("   Run: sudo bash install_ollama.sh")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Ollama timeout (may not be running)")
        print("   Run: sudo systemctl start ollama")
        return False


def check_api_keys():
    """Check if API keys are set"""
    keys_found = []
    keys_missing = []

    if os.getenv('ANTHROPIC_API_KEY'):
        keys_found.append('ANTHROPIC_API_KEY')
    else:
        keys_missing.append('ANTHROPIC_API_KEY')

    if keys_found:
        print(f"✓ API Keys: {', '.join(keys_found)}")

    if keys_missing:
        print(f"⚠️  Missing API Keys: {', '.join(keys_missing)}")
        print("   Set with: export ANTHROPIC_API_KEY='your-key'")
        return False

    return True


def check_dependencies():
    """Check required Python packages"""
    required = [
        'yaml',
        'anthropic',
        'aiohttp',
        'rich'
    ]

    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("   Run: pip install -r requirements.txt")
        return False
    else:
        print(f"✓ All required packages installed")
        return True


def check_config():
    """Check if configuration file exists"""
    config_path = Path("config/proart_px13.yaml")

    if config_path.exists():
        print(f"✓ Configuration file: {config_path}")
        return True
    else:
        print(f"❌ Configuration file missing: {config_path}")
        return False


def check_directories():
    """Check if required directories exist"""
    dirs = ['logs', 'config', 'src']
    all_exist = True

    for dir_name in dirs:
        path = Path(dir_name)
        if path.exists():
            pass  # Silent success
        else:
            print(f"❌ Directory missing: {dir_name}")
            all_exist = False

    if all_exist:
        print("✓ All required directories present")

    return all_exist


def main():
    """Run all pre-flight checks"""
    print("="*60)
    print("AutoCoder Pre-Flight Check")
    print("="*60)
    print()

    checks = {
        "Python Version": check_python_version(),
        "Directories": check_directories(),
        "Configuration": check_config(),
        "Dependencies": check_dependencies(),
        "GPU": check_gpu(),
        "Ollama": check_ollama(),
        "API Keys": check_api_keys()
    }

    print()
    print("="*60)
    print("Summary")
    print("="*60)

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    for check_name, result in checks.items():
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{check_name:.<40} {status}")

    print()
    print(f"Result: {passed}/{total} checks passed")
    print()

    # Determine readiness
    critical_checks = ["Python Version", "Configuration", "Dependencies"]
    critical_passed = all(checks.get(c, False) for c in critical_checks)

    if critical_passed:
        if checks.get("Ollama") or checks.get("API Keys"):
            print("✅ Ready to run!")
            print()
            print("Start with: python3 main.py")
            return 0
        else:
            print("⚠️  Partially ready")
            print()
            print("You need either:")
            print("  1. Ollama + local model (run: sudo bash install_ollama.sh)")
            print("  2. OR Claude API key (run: export ANTHROPIC_API_KEY='...')")
            return 1
    else:
        print("❌ Not ready - fix critical issues above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
