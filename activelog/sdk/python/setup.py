"""
ActiveLog Plugin SDK for Python
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="activelog-plugin-sdk",
    version="1.0.0",
    author="ActiveLog Team",
    author_email="sdk@activelog.ai",
    description="ActiveLog Plugin SDK for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/activelog/plugin-sdk-python",
    project_urls={
        "Bug Tracker": "https://github.com/activelog/plugin-sdk-python/issues",
        "Documentation": "https://docs.activelog.ai/sdk/python",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "pydantic>=2.0.0",
        "typing-extensions>=4.0.0",
        "asyncio-mqtt>=0.11.0",
        "jsonschema>=4.0.0",
        "redis>=4.5.0",
        "sqlalchemy[asyncio]>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
            "flake8>=6.0.0",
            "sphinx>=6.0.0",
            "sphinx-rtd-theme>=1.2.0",
        ],
        "testing": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.10.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "activelog-plugin=activelog_plugin_sdk.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)