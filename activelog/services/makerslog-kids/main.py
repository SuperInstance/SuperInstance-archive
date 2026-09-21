#!/usr/bin/env python3

import asyncio
import json
import sqlite3
import time
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import aiohttp
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import uvicorn
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MakersLogCodeChat:
    def __init__(self):
        self.service_id = "makerslog_codechat_001"
        self.name = "MakersLog CodeChat"
        self.description = "Chatbot-enabled development tool integrated into MakersLog for young makers"
        
        # Connect to our human-readable translator service
        self.translator_url = "http://localhost:8565"
        
        # Initialize database
        self.init_makerslog_database()
        
        # AI character personalities for different programming concepts
        self.code_characters = {
            "binary_bob": {
                "name": "Binary Bob",
                "personality": "Enthusiastic robot who speaks in 1s and 0s but explains things clearly",
                "specialty": "How computers think in binary",
                "catchphrase": "01001000 01101001! (That's 'Hi!' in binary!)"
            },
            "loop_lucy": {
                "name": "Loop Lucy", 
                "personality": "Energetic character who loves repetition and patterns",
                "specialty": "Loops, repetition, and patterns in code",
                "catchphrase": "Again! Again! Let's do it again (but smarter this time)!"
            },
            "function_fred": {
                "name": "Function Fred",
                "personality": "Organized librarian who keeps everything in neat boxes",
                "specialty": "Functions, organization, and code structure",
                "catchphrase": "Everything has its place, and every place has its function!"
            },
            "debug_diana": {
                "name": "Debug Diana",
                "personality": "Detective who loves solving mysteries and finding bugs",
                "specialty": "Debugging, problem-solving, and error fixing",
                "catchphrase": "Every bug is just a mystery waiting to be solved!"
            }
        }
        
        logger.info("🛠️ MakersLog CodeChat initialized")
        logger.info("🤖 AI Code Characters ready for young makers")

    def init_makerslog_database(self):
        """Initialize MakersLog development database"""
        self.conn = sqlite3.connect('makerslog_codechat.db')
        cursor = self.conn.cursor()
        
        # Young maker projects
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maker_projects (
                id INTEGER PRIMARY KEY,
                maker_name TEXT,
                project_name TEXT,
                project_type TEXT,
                difficulty_level TEXT,
                code_snippets TEXT,
                ai_helper_used TEXT,
                completion_percentage REAL,
                favorite_character TEXT,
                timestamp DATETIME
            )
        ''')
        
        # Chat sessions with code explanations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY,
                maker_name TEXT,
                character_used TEXT,
                code_snippet TEXT,
                question_asked TEXT,
                explanation_given TEXT,
                maker_rating INTEGER,
                timestamp DATETIME
            )
        ''')
        
        # Achievement system for learning
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maker_achievements (
                id INTEGER PRIMARY KEY,
                maker_name TEXT,
                achievement_type TEXT,
                achievement_name TEXT,
                description TEXT,
                code_example TEXT,
                earned_date DATETIME
            )
        ''')
        
        self.conn.commit()
        logger.info("📊 MakersLog database initialized")

    async def explain_code_for_young_maker(self, code_snippet: str, maker_name: str, character_choice: str = "binary_bob"):
        """Explain code using kid-friendly AI character"""
        logger.info(f"👦 Explaining code for young maker: {maker_name}")
        
        # Get character info
        character = self.code_characters.get(character_choice, self.code_characters["binary_bob"])
        
        # Get technical explanation from our translator service
        try:
            response = requests.post(f"{self.translator_url}/quick-explain", 
                json={
                    "code_snippet": code_snippet,
                    "user_level": "beginner"
                }, 
                timeout=10
            )
            
            if response.status_code == 200:
                technical_explanation = response.json()["quick_answer"]
            else:
                technical_explanation = "This code does something interesting!"
        except Exception as e:
            logger.warning(f"Could not get technical explanation: {e}")
            technical_explanation = "This code is doing computer magic!"
        
        # Transform technical explanation into kid-friendly character dialogue
        kid_explanation = await self._create_character_explanation(
            technical_explanation, character, code_snippet
        )
        
        # Store chat session
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO chat_sessions 
            (maker_name, character_used, code_snippet, question_asked, explanation_given, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (maker_name, character["name"], code_snippet, "What does this code do?", kid_explanation, datetime.now()))
        
        self.conn.commit()
        
        return {
            "character": character,
            "explanation": kid_explanation,
            "technical_backup": technical_explanation,
            "maker_name": maker_name,
            "follow_up_suggestions": await self._generate_follow_up_activities(code_snippet, character)
        }

    async def _create_character_explanation(self, technical_explanation: str, character: Dict, code_snippet: str) -> str:
        """Transform technical explanation into character dialogue"""
        
        character_name = character["name"]
        catchphrase = character["catchphrase"]
        
        # Character-specific explanation styles
        if "binary" in character_name.lower():
            return f"""
{catchphrase}

Hey there, young coder! {character_name} here! 🤖

I see some awesome code here! Let me break it down for you:

{technical_explanation}

Think of it like this: Your computer brain works in 1s and 0s (binary!), and this code is giving it step-by-step instructions. It's like teaching a robot friend how to do something cool!

Want to try changing something in the code and see what happens? That's how us robots learn best! 🔧✨
            """.strip()
        
        elif "loop" in character_name.lower():
            return f"""
{catchphrase}

Hi there, future programmer! {character_name} spinning in! 🌀

This code is SUPER interesting! Here's what I see:

{technical_explanation}

I LOVE when code repeats things - that's my specialty! It's like when you're jumping rope and you keep doing the same motion over and over, but each time you might jump a little higher or try a new trick!

Loops make computers really powerful because they can do boring stuff millions of times without getting tired! Want to make your own loop? 🔄
            """.strip()
        
        elif "function" in character_name.lower():
            return f"""
{catchphrase}

Greetings, organized coder! {character_name} at your service! 📚

This code is beautifully structured! Let me explain:

{technical_explanation}

I love how this code is organized! It's like having different drawers in your desk - one for pencils, one for erasers, one for stickers. Functions help us keep our code tidy and reusable!

When you write a function, you're basically creating a magic spell that you can use over and over again! 🪄
            """.strip()
        
        elif "debug" in character_name.lower():
            return f"""
{catchphrase}

Hello there, detective-in-training! {character_name} on the case! 🔍

I'm examining this code like a mystery to solve:

{technical_explanation}

Every piece of code tells a story, and sometimes there are plot twists (we call them bugs)! The cool thing is, even when code doesn't work perfectly at first, that's just part of the adventure!

Remember: Every expert programmer started as a beginner who never gave up! 🕵️‍♀️
            """.strip()
        
        else:
            return f"""
Hey there! 😊

{technical_explanation}

Code is like giving instructions to a computer friend. The more specific and clear you are, the better your computer friend can help you build amazing things!

Keep coding, keep creating! 🚀
            """.strip()

    async def _generate_follow_up_activities(self, code_snippet: str, character: Dict) -> List[str]:
        """Generate follow-up learning activities"""
        activities = [
            f"Try changing one number in the code and run it again!",
            f"Ask {character['name']} to explain a different part of the code",
            f"Draw a picture of what you think this code does",
            f"Try writing your own version of this code",
            f"Show this code to a friend or family member and explain it to them"
        ]
        
        return activities

    async def create_maker_project(self, maker_name: str, project_name: str, project_type: str):
        """Create a new maker project with AI assistance"""
        logger.info(f"🎨 Creating new maker project: {project_name}")
        
        # Generate project starter code based on type
        starter_code = await self._generate_starter_code(project_type)
        
        # Create project record
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO maker_projects 
            (maker_name, project_name, project_type, difficulty_level, code_snippets, completion_percentage, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (maker_name, project_name, project_type, "beginner", starter_code, 0.0, datetime.now()))
        
        project_id = cursor.lastrowid
        self.conn.commit()
        
        return {
            "project_id": project_id,
            "project_name": project_name,
            "starter_code": starter_code,
            "next_steps": await self._generate_project_next_steps(project_type),
            "helpful_character": self._recommend_character_for_project(project_type)
        }

    async def _generate_starter_code(self, project_type: str) -> str:
        """Generate beginner-friendly starter code"""
        templates = {
            "drawing": '''# Let's draw something cool!
import turtle

# Create our drawing friend
pen = turtle.Turtle()
pen.color("blue")

# Draw a square
for i in range(4):
    pen.forward(100)
    pen.right(90)

# Keep the window open
turtle.done()''',
            
            "game": '''# Simple guessing game
import random

# Computer picks a number
secret_number = random.randint(1, 10)
print("I'm thinking of a number between 1 and 10!")

# Player guesses
guess = int(input("What's your guess? "))

if guess == secret_number:
    print("WOW! You got it! 🎉")
else:
    print(f"Good try! The number was {secret_number}")''',
    
            "calculator": '''# Magic Calculator
print("Welcome to your Magic Calculator! ✨")

# Get numbers from user
first_number = float(input("Enter first number: "))
second_number = float(input("Enter second number: "))

# Do math magic
result = first_number + second_number

print(f"The magic answer is: {result}")''',

            "story": '''# Story Generator
import random

characters = ["a brave knight", "a clever wizard", "a friendly dragon"]
places = ["in a magical forest", "on a floating island", "in a crystal cave"]
adventures = ["found a treasure chest", "discovered a secret door", "met a talking animal"]

# Pick random story parts
character = random.choice(characters)
place = random.choice(places)
adventure = random.choice(adventures)

print(f"Once upon a time, {character} {place} {adventure}!")'''
        }
        
        return templates.get(project_type, templates["drawing"])

    def _recommend_character_for_project(self, project_type: str) -> str:
        """Recommend the best AI character for each project type"""
        recommendations = {
            "drawing": "loop_lucy",  # Loops are great for drawing
            "game": "debug_diana",   # Games need debugging
            "calculator": "function_fred",  # Functions for organization
            "story": "binary_bob"    # Binary for random choices
        }
        
        return recommendations.get(project_type, "binary_bob")

# FastAPI app setup
app = FastAPI(
    title="MakersLog CodeChat - Development Tool for Young Makers",
    description="Chatbot-enabled development tool with AI characters to teach coding to kids",
    version="1.0.0"
)

# Global service instance
makerslog_chat = MakersLogCodeChat()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": makerslog_chat.name,
        "description": makerslog_chat.description,
        "characters": list(makerslog_chat.code_characters.keys()),
        "status": "ready_to_help_young_makers"
    }

@app.post("/explain-code")
async def explain_code(request: dict):
    """Explain code with AI character for young makers"""
    code_snippet = request.get("code_snippet", "")
    maker_name = request.get("maker_name", "Young Maker")
    character_choice = request.get("character", "binary_bob")
    
    if not code_snippet:
        raise HTTPException(status_code=400, detail="code_snippet is required")
    
    explanation = await makerslog_chat.explain_code_for_young_maker(
        code_snippet, maker_name, character_choice
    )
    return explanation

@app.post("/create-project")
async def create_project(request: dict):
    """Create new maker project with AI assistance"""
    maker_name = request.get("maker_name", "")
    project_name = request.get("project_name", "")
    project_type = request.get("project_type", "drawing")
    
    if not maker_name or not project_name:
        raise HTTPException(status_code=400, detail="maker_name and project_name are required")
    
    project = await makerslog_chat.create_maker_project(maker_name, project_name, project_type)
    return project

@app.get("/characters")
async def get_characters():
    """Get available AI characters"""
    return {
        "characters": makerslog_chat.code_characters,
        "total": len(makerslog_chat.code_characters)
    }

@app.get("/maker/{maker_name}/projects")
async def get_maker_projects(maker_name: str):
    """Get projects for a specific maker"""
    cursor = makerslog_chat.conn.cursor()
    cursor.execute('SELECT * FROM maker_projects WHERE maker_name = ? ORDER BY timestamp DESC', (maker_name,))
    projects = cursor.fetchall()
    
    return {
        "maker_name": maker_name,
        "project_count": len(projects),
        "projects": [
            {
                "id": p[0],
                "name": p[2],
                "type": p[3],
                "difficulty": p[4],
                "completion": f"{p[6]:.1%}",
                "created": p[8]
            }
            for p in projects
        ]
    }

if __name__ == "__main__":
    import os
    
    logger.info("🚀 Starting MakersLog CodeChat")
    logger.info("🛠️ Development tool for young makers with AI characters")
    logger.info("👦👧 Making coding fun and accessible for kids")
    
    port = int(os.environ.get("PORT", 8570))
    uvicorn.run(app, host="0.0.0.0", port=port)