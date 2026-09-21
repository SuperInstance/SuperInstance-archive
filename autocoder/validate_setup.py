#!/usr/bin/env python3
"""
Hardware Validation Script for ProArt PX13
Tests GPU, RAM, storage, and model compatibility
"""

import sys
import subprocess
import platform
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓{Colors.END} {text}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠{Colors.END} {text}")

def print_error(text):
    print(f"{Colors.RED}✗{Colors.END} {text}")

def run_command(cmd, shell=False):
    """Run command and return output"""
    try:
        if shell:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        else:
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=5)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_os():
    """Check operating system"""
    print_header("Operating System Check")

    os_type = platform.system()
    os_release = platform.release()

    if os_type == "Linux":
        # Check if WSL
        success, output, _ = run_command("uname -r", shell=True)
        if success and "microsoft" in output.lower():
            print_success(f"WSL2 detected: {os_release}")
            print_warning("Make sure GPU passthrough is configured for CUDA")
            return True
        else:
            print_success(f"Linux: {platform.platform()}")
            return True
    elif os_type == "Windows":
        print_success(f"Windows: {os_release}")
        print_warning("Consider using WSL2 for better compatibility")
        return True
    else:
        print_warning(f"Untested OS: {os_type}")
        return True

def check_gpu():
    """Check NVIDIA GPU availability"""
    print_header("GPU Check (RTX 4050)")

    # Try nvidia-smi
    success, output, error = run_command("nvidia-smi")

    if not success:
        print_error("nvidia-smi not found")
        print_warning("Install NVIDIA drivers from: https://www.nvidia.com/Download/index.aspx")
        return False

    # Parse output for GPU info
    if "RTX 4050" in output:
        print_success("RTX 4050 detected")

        # Check VRAM
        success, output, _ = run_command("nvidia-smi --query-gpu=memory.total --format=csv,noheader")
        if success:
            vram = output.strip()
            print_success(f"VRAM available: {vram}")

            # Check if approximately 6GB
            vram_mb = int(vram.split()[0])
            if 5500 <= vram_mb <= 6500:
                print_success("VRAM matches expected 6GB")
            else:
                print_warning(f"Expected ~6GB VRAM, got {vram_mb}MB")

        # Check CUDA version
        success, output, _ = run_command("nvidia-smi")
        if "CUDA Version" in output:
            for line in output.split('\n'):
                if "CUDA Version" in line:
                    cuda_version = line.split("CUDA Version:")[1].split()[0]
                    print_success(f"CUDA version: {cuda_version}")

        return True
    else:
        print_warning("GPU detected but not RTX 4050")
        print(output)
        return False

def check_ram():
    """Check system RAM"""
    print_header("System RAM Check")

    try:
        import psutil
        ram = psutil.virtual_memory()
        total_gb = ram.total / (1024**3)

        print_success(f"Total RAM: {total_gb:.1f} GB")

        if total_gb >= 30:
            print_success("RAM sufficient for CPU inference (32GB expected)")
        elif total_gb >= 16:
            print_warning("RAM lower than expected (32GB), but workable")
        else:
            print_error("RAM too low for CPU inference")
            return False

        available_gb = ram.available / (1024**3)
        print_success(f"Available RAM: {available_gb:.1f} GB ({ram.percent}% used)")

        return True
    except ImportError:
        print_warning("psutil not installed, skipping RAM check")
        print("Install with: pip install psutil")
        return True

def check_storage():
    """Check storage space"""
    print_header("Storage Check")

    try:
        import shutil
        total, used, free = shutil.disk_usage("/")

        total_gb = total / (1024**3)
        free_gb = free / (1024**3)

        print_success(f"Total storage: {total_gb:.1f} GB")
        print_success(f"Free space: {free_gb:.1f} GB")

        if free_gb < 50:
            print_warning("Less than 50GB free. Models require 5-20GB each.")
        elif free_gb < 100:
            print_warning("Consider freeing space for multiple models")
        else:
            print_success("Plenty of storage for models")

        return True
    except Exception as e:
        print_error(f"Storage check failed: {e}")
        return False

def check_python():
    """Check Python version"""
    print_header("Python Environment")

    version = sys.version_info
    print_success(f"Python {version.major}.{version.minor}.{version.micro}")

    if version.major == 3 and version.minor >= 10:
        print_success("Python version compatible")
    else:
        print_warning(f"Python 3.10+ recommended, you have {version.major}.{version.minor}")

    # Check virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if in_venv:
        print_success("Running in virtual environment")
    else:
        print_warning("Not in virtual environment. Create one with: python3 -m venv venv")

    return True

def check_ollama():
    """Check if Ollama is installed"""
    print_header("Ollama Installation")

    success, output, _ = run_command("ollama --version")

    if success:
        version = output.strip()
        print_success(f"Ollama installed: {version}")

        # Check if models are pulled
        success, output, _ = run_command("ollama list")
        if success:
            models = output.strip().split('\n')[1:]  # Skip header
            if models and models[0]:
                print_success(f"Models installed: {len(models)}")
                for model in models[:5]:  # Show first 5
                    print(f"  - {model.split()[0]}")

                # Check for recommended models
                model_names = [m.split()[0] for m in models]
                if any('qwen2.5-coder:7b' in m for m in model_names):
                    print_success("Recommended model (qwen2.5-coder:7b) found")
                else:
                    print_warning("Recommended model not found. Pull with:")
                    print("  ollama pull qwen2.5-coder:7b-instruct-q4_K_M")
            else:
                print_warning("No models installed yet")
                print("Pull recommended model: ollama pull qwen2.5-coder:7b-instruct-q4_K_M")
        return True
    else:
        print_error("Ollama not installed")
        print("Install with: curl -fsSL https://ollama.com/install.sh | sh")
        return False

def check_dependencies():
    """Check Python dependencies"""
    print_header("Python Dependencies")

    required = {
        'anthropic': 'Anthropic API',
        'openai': 'OpenAI API',
        'rich': 'Terminal UI',
        'prompt_toolkit': 'CLI framework',
        'aiohttp': 'Async HTTP',
        'aiofiles': 'Async file I/O',
        'psutil': 'System monitoring',
        'pyyaml': 'Config files'
    }

    missing = []
    for package, description in required.items():
        try:
            __import__(package)
            print_success(f"{package:20} - {description}")
        except ImportError:
            print_error(f"{package:20} - {description} (MISSING)")
            missing.append(package)

    if missing:
        print(f"\n{Colors.YELLOW}Install missing packages:{Colors.END}")
        print(f"  pip install {' '.join(missing)}")
        return False

    return True

def check_api_keys():
    """Check API keys"""
    print_header("API Keys")

    import os

    keys = {
        'ANTHROPIC_API_KEY': 'Claude API',
        'OPENAI_API_KEY': 'OpenAI API (optional)',
    }

    for key, name in keys.items():
        if os.getenv(key):
            print_success(f"{name:20} - Configured")
        else:
            if key == 'ANTHROPIC_API_KEY':
                print_warning(f"{name:20} - Not set (required for cloud)")
            else:
                print_warning(f"{name:20} - Not set (optional)")

    if not os.getenv('ANTHROPIC_API_KEY'):
        print(f"\n{Colors.YELLOW}Set API key:{Colors.END}")
        print(f"  export ANTHROPIC_API_KEY='your-key-here'")
        print(f"  Or add to ~/.bashrc")

    return True

def test_gpu_inference():
    """Test actual GPU inference"""
    print_header("GPU Inference Test")

    print("Testing Ollama GPU inference (this may take 10-20 seconds)...")

    success, output, error = run_command(
        'ollama run qwen2.5-coder:7b-instruct-q4_K_M "Write a hello world function in Python" --verbose',
        shell=True
    )

    if success:
        print_success("GPU inference working!")
        if output:
            print(f"\n{Colors.BLUE}Model response:{Colors.END}")
            print(output[:500])  # First 500 chars
    else:
        print_error("GPU inference failed")
        if "model not found" in error.lower():
            print_warning("Model not installed. Run:")
            print("  ollama pull qwen2.5-coder:7b-instruct-q4_K_M")
        else:
            print(error)
        return False

    return True

def main():
    """Run all checks"""
    print(f"""
{Colors.BOLD}{Colors.BLUE}
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║         ProArt PX13 Hardware Validation Script          ║
║              For AutoCoder Setup                         ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
{Colors.END}
    """)

    checks = [
        ("Operating System", check_os),
        ("GPU (RTX 4050)", check_gpu),
        ("System RAM", check_ram),
        ("Storage", check_storage),
        ("Python", check_python),
        ("Ollama", check_ollama),
        ("Dependencies", check_dependencies),
        ("API Keys", check_api_keys),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print_error(f"Check failed with error: {e}")
            results[name] = False

    # Summary
    print_header("Summary")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for name, result in results.items():
        if result:
            print_success(f"{name:30} PASSED")
        else:
            print_error(f"{name:30} FAILED")

    print(f"\n{Colors.BOLD}Total: {passed}/{total} checks passed{Colors.END}")

    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All checks passed! Ready to start building.{Colors.END}")
        print(f"\n{Colors.BLUE}Next steps:{Colors.END}")
        print(f"  1. Follow PROART_PX13_SETUP.md for laptop-specific setup")
        print(f"  2. Follow QUICK_START.md to build the MVP")
        print(f"  3. Run test inference to verify GPU speed")
        return 0
    elif passed >= total * 0.7:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Most checks passed. Review warnings above.{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Several checks failed. Fix issues above before continuing.{Colors.END}")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Validation interrupted{Colors.END}")
        sys.exit(130)
