#!/usr/bin/env python3
"""
Setup script for ActiveLog Sync Service v2
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open('README.md', 'r', encoding='utf-8') as f:
        return f.read()

# Read requirements
def read_requirements():
    requirements = []
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r') as f:
            requirements = f.read().splitlines()
    return requirements

setup(
    name='activelog-sync-v2',
    version='2.0.0',
    description='Advanced device synchronization service for ActiveLog.ai',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    author='ActiveLog.ai Team',
    author_email='dev@activelog.ai',
    url='https://github.com/activelogai/sync-v2',
    
    packages=find_packages(),
    
    install_requires=[
        'asyncio',
        'websockets>=11.0.0',
        'aiohttp>=3.8.0',
        'sqlite3',
        'dataclasses',
        'typing-extensions',
    ],
    
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
        ],
        'mobile': [
            'pybluez>=0.23',
            'wifi>=0.3.8',
        ],
        'collaboration': [
            'redis>=4.5.0',
        ],
        'monitoring': [
            'prometheus-client>=0.16.0',
        ]
    },
    
    entry_points={
        'console_scripts': [
            'activelog-sync=sync_service:main',
        ],
    },
    
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: System :: Networking',
    ],
    
    python_requires='>=3.8',
    
    include_package_data=True,
    zip_safe=False,
)