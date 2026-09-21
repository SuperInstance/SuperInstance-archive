#!/usr/bin/env python3
"""
Director Terminal - Multi-Bot Orchestration Command Center
A web-based terminal interface for managing the bot orchestration system
Port: 8480
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional
import aiohttp
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/activeloguser/activelog/logs/director-terminal.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
ORCHESTRATOR_URL = "http://localhost:8450"
TERMINAL_PORT = 8480

class DirectorTerminal:
    def __init__(self):
        self.connected_clients: List[WebSocket] = []
        self.command_history: List[Dict[str, Any]] = []
        self.system_status = {"status": "unknown", "last_check": None}
        
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if self.connected_clients:
            disconnected = []
            for client in self.connected_clients:
                try:
                    await client.send_json(message)
                except:
                    disconnected.append(client)
            
            # Remove disconnected clients
            for client in disconnected:
                if client in self.connected_clients:
                    self.connected_clients.remove(client)
    
    async def execute_command(self, command: str, args: List[str] = None) -> Dict[str, Any]:
        """Execute a terminal command and return result"""
        args = args or []
        timestamp = datetime.now().isoformat()
        
        try:
            # System commands
            if command == "status":
                return await self.get_system_status()
            elif command == "help":
                return self.get_help()
            elif command == "clear":
                return {"type": "clear", "timestamp": timestamp}
            elif command == "tasks":
                return await self.list_tasks(args)
            elif command == "submit":
                return await self.submit_task(args)
            elif command == "execute":
                return await self.execute_task(args)
            elif command == "bots":
                return await self.list_bots(args)
            elif command == "health":
                return await self.check_health(args)
            elif command == "metrics":
                return await self.get_metrics()
            elif command == "context":
                return await self.manage_context(args)
            elif command == "knowledge":
                return await self.manage_knowledge(args)
            elif command == "share":
                return await self.share_information(args)
            else:
                return {
                    "type": "error",
                    "message": f"Unknown command: {command}",
                    "timestamp": timestamp
                }
        
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return {
                "type": "error",
                "message": f"Command failed: {str(e)}",
                "timestamp": timestamp
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get orchestration system status"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ORCHESTRATOR_URL}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.system_status = {
                            "status": "healthy",
                            "last_check": datetime.now().isoformat(),
                            "uptime": data.get("uptime_seconds", 0),
                            "components": data.get("components", {})
                        }
                    else:
                        self.system_status = {
                            "status": "error",
                            "last_check": datetime.now().isoformat(),
                            "error": f"HTTP {response.status}"
                        }
        except Exception as e:
            self.system_status = {
                "status": "offline",
                "last_check": datetime.now().isoformat(),
                "error": str(e)
            }
        
        return {
            "type": "status",
            "data": self.system_status,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_help(self) -> Dict[str, Any]:
        """Get help information"""
        commands = {
            "status": "Check orchestration system status",
            "tasks": "List tasks (add 'queue' for queue status)",
            "submit <description>": "Submit a new task",
            "execute <task_id>": "Execute a specific task",
            "bots": "List registered bots",
            "health [bot_id]": "Check system or bot health",
            "metrics": "Get system metrics",
            "context add <type> <content>": "Add context information",
            "knowledge add <content>": "Add to knowledge graph",
            "share <type> <title> <content>": "Share information",
            "clear": "Clear terminal",
            "help": "Show this help message"
        }
        
        return {
            "type": "help",
            "commands": commands,
            "timestamp": datetime.now().isoformat()
        }
    
    async def list_tasks(self, args: List[str]) -> Dict[str, Any]:
        """List tasks or queue status"""
        try:
            if args and args[0] == "queue":
                endpoint = "/tasks/queue/status"
            else:
                endpoint = "/tasks/queue/status"  # Default to queue status
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ORCHESTRATOR_URL}{endpoint}") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "type": "tasks",
                            "data": data,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "type": "error",
                            "message": f"Failed to get tasks: HTTP {response.status}",
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            return {
                "type": "error",
                "message": f"Failed to get tasks: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def submit_task(self, args: List[str]) -> Dict[str, Any]:
        """Submit a new task"""
        if not args:
            return {
                "type": "error",
                "message": "Usage: submit <task_description>",
                "timestamp": datetime.now().isoformat()
            }
        
        description = " ".join(args)
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "description": description,
                    "priority": "MEDIUM",
                    "estimated_tokens": 5000
                }
                
                async with session.post(f"{ORCHESTRATOR_URL}/tasks/submit", json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "type": "task_submitted",
                            "data": data,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "type": "error",
                            "message": f"Failed to submit task: HTTP {response.status}",
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            return {
                "type": "error",
                "message": f"Failed to submit task: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def execute_task(self, args: List[str]) -> Dict[str, Any]:
        """Execute a specific task"""
        if not args:
            return {
                "type": "error",
                "message": "Usage: execute <task_id>",
                "timestamp": datetime.now().isoformat()
            }
        
        task_id = args[0]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{ORCHESTRATOR_URL}/tasks/{task_id}/execute") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "type": "task_executed",
                            "data": data,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "type": "error",
                            "message": f"Failed to execute task: HTTP {response.status}",
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            return {
                "type": "error",
                "message": f"Failed to execute task: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def list_bots(self, args: List[str]) -> Dict[str, Any]:
        """List registered bots"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ORCHESTRATOR_URL}/bots/health/overview") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "type": "bots",
                            "data": data,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "type": "error",
                            "message": f"Failed to get bots: HTTP {response.status}",
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            return {
                "type": "error",
                "message": f"Failed to get bots: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def check_health(self, args: List[str]) -> Dict[str, Any]:
        """Check system or bot health"""
        if args:
            bot_id = args[0]
            endpoint = f"/bots/{bot_id}/health"
        else:
            endpoint = "/bots/health/overview"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ORCHESTRATOR_URL}{endpoint}") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "type": "health",
                            "data": data,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "type": "error",
                            "message": f"Failed to get health: HTTP {response.status}",
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            return {
                "type": "error",
                "message": f"Failed to get health: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ORCHESTRATOR_URL}/metrics") as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "type": "metrics",
                            "data": data,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "type": "error",
                            "message": f"Failed to get metrics: HTTP {response.status}",
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            return {
                "type": "error",
                "message": f"Failed to get metrics: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def manage_context(self, args: List[str]) -> Dict[str, Any]:
        """Manage context information"""
        if not args or args[0] != "add" or len(args) < 3:
            return {
                "type": "error",
                "message": "Usage: context add <type> <content>",
                "timestamp": datetime.now().isoformat()
            }
        
        context_type = args[1]
        content = " ".join(args[2:])
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "context_type": context_type.upper(),
                    "content": content,
                    "priority": "MEDIUM"
                }
                
                async with session.post(f"{ORCHESTRATOR_URL}/context/add", json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "type": "context_added",
                            "data": data,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "type": "error",
                            "message": f"Failed to add context: HTTP {response.status}",
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            return {
                "type": "error",
                "message": f"Failed to add context: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def manage_knowledge(self, args: List[str]) -> Dict[str, Any]:
        """Manage knowledge graph"""
        if not args or args[0] != "add" or len(args) < 2:
            return {
                "type": "error",
                "message": "Usage: knowledge add <content>",
                "timestamp": datetime.now().isoformat()
            }
        
        content = " ".join(args[1:])
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "content": content,
                    "content_type": "terminal_input",
                    "source": "director_terminal"
                }
                
                async with session.post(f"{ORCHESTRATOR_URL}/knowledge/add", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "type": "knowledge_added",
                            "data": data,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "type": "error",
                            "message": f"Failed to add knowledge: HTTP {response.status}",
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            return {
                "type": "error",
                "message": f"Failed to add knowledge: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def share_information(self, args: List[str]) -> Dict[str, Any]:
        """Share information between bots"""
        if len(args) < 3:
            return {
                "type": "error",
                "message": "Usage: share <type> <title> <content>",
                "timestamp": datetime.now().isoformat()
            }
        
        info_type = args[0]
        title = args[1]
        content = " ".join(args[2:])
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "info_type": info_type.upper(),
                    "title": title,
                    "content": content,
                    "scope": "TEAM_LEVEL",
                    "priority": "MEDIUM"
                }
                
                async with session.post(f"{ORCHESTRATOR_URL}/information/share", json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "type": "information_shared",
                            "data": data,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "type": "error",
                            "message": f"Failed to share information: HTTP {response.status}",
                            "timestamp": datetime.now().isoformat()
                        }
        except Exception as e:
            return {
                "type": "error",
                "message": f"Failed to share information: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

# Global terminal instance
terminal = DirectorTerminal()

# FastAPI app
app = FastAPI(
    title="Director Terminal",
    description="Multi-Bot Orchestration Command Center",
    version="1.0.0"
)

# Templates and static files
templates = Jinja2Templates(directory="/home/activeloguser/activelog/services/director-terminal/templates")

@app.get("/", response_class=HTMLResponse)
async def get_terminal(request: Request):
    """Serve the terminal interface"""
    return templates.TemplateResponse("terminal.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for terminal communication"""
    await websocket.accept()
    terminal.connected_clients.append(websocket)
    
    # Send welcome message
    welcome_msg = {
        "type": "welcome",
        "message": "Director Terminal connected. Type 'help' for commands.",
        "timestamp": datetime.now().isoformat()
    }
    await websocket.send_json(welcome_msg)
    
    try:
        while True:
            # Receive command from client
            data = await websocket.receive_json()
            command_line = data.get("command", "").strip()
            
            if not command_line:
                continue
            
            # Parse command and arguments
            parts = command_line.split()
            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            
            # Execute command
            result = await terminal.execute_command(command, args)
            
            # Send result back to client
            await websocket.send_json(result)
            
            # Add to command history
            terminal.command_history.append({
                "command": command_line,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            # Broadcast to all clients if it's a system update
            if result.get("type") in ["status", "task_submitted", "task_executed"]:
                await terminal.broadcast_message(result)
                
    except WebSocketDisconnect:
        if websocket in terminal.connected_clients:
            terminal.connected_clients.remove(websocket)

@app.get("/api/status")
async def api_status():
    """Get terminal status via REST API"""
    return {
        "connected_clients": len(terminal.connected_clients),
        "system_status": terminal.system_status,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "director-terminal",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("/home/activeloguser/activelog/services/director-terminal/templates", exist_ok=True)
    os.makedirs("/home/activeloguser/activelog/logs", exist_ok=True)
    
    # Start server
    logger.info(f"Starting Director Terminal on port {TERMINAL_PORT}")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=TERMINAL_PORT,
        log_level="info"
    )