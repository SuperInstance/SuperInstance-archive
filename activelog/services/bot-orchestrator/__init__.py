"""
Bot Orchestration System

An intelligent bot orchestration system with Claude Opus 4.1 director integration.
Provides advanced multi-bot coordination, context management, and knowledge sharing.
"""

__version__ = "1.0.0"
__author__ = "Claude Code"
__description__ = "Intelligent Bot Orchestration System"

from . import director, coordination, context, shared

__all__ = ['director', 'coordination', 'context', 'shared']