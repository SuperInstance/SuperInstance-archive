#!/usr/bin/env python3
"""
Test that all Python imports work correctly
Run this to verify the virtual environment is set up properly
"""

import sys
print(f"Python: {sys.version}")
print()

tests = []

# Test FastAPI and web server
try:
    import fastapi
    import uvicorn
    import websockets
    tests.append(("✓", "FastAPI & Uvicorn", f"fastapi {fastapi.__version__}"))
except ImportError as e:
    tests.append(("✗", "FastAPI & Uvicorn", str(e)))

# Test Anthropic Claude API
try:
    import anthropic
    tests.append(("✓", "Anthropic", f"anthropic {anthropic.__version__}"))
except ImportError as e:
    tests.append(("✗", "Anthropic", str(e)))

# Test Ollama
try:
    import ollama
    tests.append(("✓", "Ollama", "ollama 0.1.0"))
except ImportError as e:
    tests.append(("✗", "Ollama", str(e)))

# Test ChromaDB
try:
    import chromadb
    tests.append(("✓", "ChromaDB", f"chromadb {chromadb.__version__}"))
except ImportError as e:
    tests.append(("✗", "ChromaDB", str(e)))

# Test SQLAlchemy
try:
    import sqlalchemy
    tests.append(("✓", "SQLAlchemy", f"sqlalchemy {sqlalchemy.__version__}"))
except ImportError as e:
    tests.append(("✗", "SQLAlchemy", str(e)))

# Test Pydantic
try:
    import pydantic
    tests.append(("✓", "Pydantic", f"pydantic {pydantic.__version__}"))
except ImportError as e:
    tests.append(("✗", "Pydantic", str(e)))

# Test PyYAML
try:
    import yaml
    tests.append(("✓", "PyYAML", "yaml"))
except ImportError as e:
    tests.append(("✗", "PyYAML", str(e)))

# Test dotenv
try:
    import dotenv
    tests.append(("✓", "python-dotenv", "dotenv"))
except ImportError as e:
    tests.append(("✗", "python-dotenv", str(e)))

# Print results
print("=" * 60)
print("DEPENDENCY CHECK")
print("=" * 60)
for status, name, version in tests:
    print(f"{status} {name:20s} {version}")

print("=" * 60)

# Summary
passed = sum(1 for s, _, _ in tests if s == "✓")
failed = sum(1 for s, _, _ in tests if s == "✗")

print(f"\nPassed: {passed}/{len(tests)}")
if failed > 0:
    print(f"Failed: {failed}/{len(tests)}")
    print("\nRun: pip install -r requirements-minimal.txt")
    sys.exit(1)
else:
    print("\n✓ All dependencies installed correctly!")
    sys.exit(0)
