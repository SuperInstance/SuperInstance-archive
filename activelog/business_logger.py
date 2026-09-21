#!/usr/bin/env python3
"""
BusinessLog Service - Meeting Notes & Task Tracking
Simple backend for business logging with meeting notes and task management
"""

import asyncio
import json
import time
import uuid
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field, validator
import uvicorn

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Data Models
class MeetingNote(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    notes: str
    date: str
    attendees: List[str] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str = ""
    priority: str = Field(default="medium", pattern=r'^(low|medium|high|urgent)$')
    status: str = Field(default="todo", pattern=r'^(todo|in_progress|done|cancelled)$')
    due_date: Optional[str] = None
    assigned_to: Optional[str] = None
    meeting_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class BusinessLogBackend:
    """BusinessLog backend service"""
    
    def __init__(self):
        self.db_path = Path("data/businesslog.db")
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_database()
        
        # Performance metrics
        self.metrics = {
            "requests_served": 0,
            "meetings_created": 0,
            "tasks_created": 0,
            "database_queries": 0,
        }
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute('PRAGMA foreign_keys = ON')
        cursor.execute('PRAGMA journal_mode = WAL')
        
        # Meeting notes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                notes TEXT NOT NULL,
                date TEXT NOT NULL,
                attendees TEXT DEFAULT '[]',
                action_items TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
                status TEXT DEFAULT 'todo' CHECK (status IN ('todo', 'in_progress', 'done', 'cancelled')),
                due_date TEXT,
                assigned_to TEXT,
                meeting_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (meeting_id) REFERENCES meetings (id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_meeting ON tasks(meeting_id)')
        
        conn.commit()
        conn.close()
        logger.info("✅ BusinessLog database initialized")
    
    def get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        self.metrics["database_queries"] += 1
        return conn
    
    async def create_meeting(self, meeting: MeetingNote) -> MeetingNote:
        """Create new meeting note"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO meetings (id, title, notes, date, attendees, action_items)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            meeting.id,
            meeting.title,
            meeting.notes,
            meeting.date,
            json.dumps(meeting.attendees),
            json.dumps(meeting.action_items)
        ))
        
        conn.commit()
        conn.close()
        
        self.metrics["meetings_created"] += 1
        logger.info(f"📝 Created meeting: {meeting.title}")
        return meeting
    
    async def get_meetings(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get meeting notes"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM meetings 
            ORDER BY date DESC, created_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        meetings = []
        for row in cursor.fetchall():
            meetings.append({
                'id': row['id'],
                'title': row['title'],
                'notes': row['notes'],
                'date': row['date'],
                'attendees': json.loads(row['attendees']),
                'action_items': json.loads(row['action_items']),
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
        
        conn.close()
        return meetings
    
    async def create_task(self, task: Task) -> Task:
        """Create new task"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tasks (id, title, description, priority, status, due_date, assigned_to, meeting_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task.id,
            task.title,
            task.description,
            task.priority,
            task.status,
            task.due_date,
            task.assigned_to,
            task.meeting_id
        ))
        
        conn.commit()
        conn.close()
        
        self.metrics["tasks_created"] += 1
        logger.info(f"✅ Created task: {task.title}")
        return task
    
    async def get_tasks(self, status: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get tasks"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT * FROM tasks 
                WHERE status = ?
                ORDER BY priority DESC, due_date ASC, created_at DESC
                LIMIT ? OFFSET ?
            ''', (status, limit, offset))
        else:
            cursor.execute('''
                SELECT * FROM tasks 
                ORDER BY priority DESC, due_date ASC, created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'priority': row['priority'],
                'status': row['status'],
                'due_date': row['due_date'],
                'assigned_to': row['assigned_to'],
                'meeting_id': row['meeting_id'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
        
        conn.close()
        return tasks
    
    async def update_task(self, task_id: str, updates: Dict) -> bool:
        """Update task"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Build dynamic update query
        update_fields = []
        values = []
        
        for field in ['title', 'description', 'priority', 'status', 'due_date', 'assigned_to']:
            if field in updates:
                update_fields.append(f"{field} = ?")
                values.append(updates[field])
        
        if not update_fields:
            return False
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(task_id)
        
        query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, values)
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            logger.info(f"🔄 Updated task: {task_id}")
        
        return success

# Initialize backend service
backend = BusinessLogBackend()

# FastAPI app
app = FastAPI(
    title="BusinessLog Service",
    description="Meeting notes and task tracking for business productivity",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Web interface HTML
WEB_INTERFACE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BusinessLog - Meeting Notes & Task Tracking</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            color: #334155;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            color: #1e293b;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        
        .header p {
            color: #64748b;
            font-size: 1.1em;
        }
        
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        .panel {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-top: 4px solid #3b82f6;
        }
        
        .panel h2 {
            color: #1e293b;
            margin-bottom: 20px;
            font-size: 1.5em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .form-group {
            margin-bottom: 16px;
        }
        
        label {
            display: block;
            margin-bottom: 6px;
            font-weight: 600;
            color: #374151;
        }
        
        input, textarea, select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.2s;
        }
        
        input:focus, textarea:focus, select:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        
        textarea {
            min-height: 100px;
            resize: vertical;
        }
        
        button {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s;
            font-size: 14px;
        }
        
        button:hover {
            background: #2563eb;
        }
        
        .btn-secondary {
            background: #6b7280;
        }
        
        .btn-secondary:hover {
            background: #4b5563;
        }
        
        .btn-success {
            background: #10b981;
        }
        
        .btn-success:hover {
            background: #059669;
        }
        
        .item-list {
            margin-top: 20px;
        }
        
        .meeting-item, .task-item {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .meeting-item:hover, .task-item:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        .meeting-item h4, .task-item h4 {
            color: #1e293b;
            margin-bottom: 8px;
            font-size: 1.1em;
        }
        
        .meeting-date {
            color: #6b7280;
            font-size: 0.9em;
            margin-bottom: 8px;
        }
        
        .task-meta {
            display: flex;
            gap: 12px;
            margin-top: 8px;
            flex-wrap: wrap;
        }
        
        .badge {
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.8em;
            font-weight: 600;
        }
        
        .priority-high { background: #fee2e2; color: #dc2626; }
        .priority-urgent { background: #fef2f2; color: #991b1b; }
        .priority-medium { background: #fef3c7; color: #d97706; }
        .priority-low { background: #ecfdf5; color: #059669; }
        
        .status-todo { background: #f3f4f6; color: #374151; }
        .status-in_progress { background: #dbeafe; color: #1d4ed8; }
        .status-done { background: #d1fae5; color: #065f46; }
        .status-cancelled { background: #fee2e2; color: #dc2626; }
        
        .attendees-list {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 8px;
        }
        
        .attendee {
            background: #e0e7ff;
            color: #3730a3;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
        }
        
        .action-items {
            margin-top: 8px;
        }
        
        .action-item {
            background: #fff7ed;
            border-left: 3px solid #f97316;
            padding: 8px 12px;
            margin: 4px 0;
            border-radius: 0 4px 4px 0;
            font-size: 0.9em;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #3b82f6;
        }
        
        .stat-label {
            color: #6b7280;
            font-size: 0.9em;
            margin-top: 4px;
        }
        
        @media (max-width: 768px) {
            .main-grid {
                grid-template-columns: 1fr;
            }
            
            .container {
                padding: 15px;
            }
            
            .header h1 {
                font-size: 2em;
            }
        }
        
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #6b7280;
        }
        
        .empty-state-icon {
            font-size: 3em;
            margin-bottom: 16px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏢 BusinessLog</h1>
            <p>Professional meeting notes and task tracking for your team</p>
        </div>

        <div class="stats" id="statsContainer">
            <div class="stat-card">
                <div class="stat-number" id="meetingCount">0</div>
                <div class="stat-label">Total Meetings</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="taskCount">0</div>
                <div class="stat-label">Active Tasks</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="completedCount">0</div>
                <div class="stat-label">Completed Tasks</div>
            </div>
        </div>

        <div class="main-grid">
            <!-- Meeting Notes Panel -->
            <div class="panel">
                <h2>📝 Meeting Notes</h2>
                
                <form id="meetingForm">
                    <div class="form-group">
                        <label>Meeting Title</label>
                        <input type="text" id="meetingTitle" placeholder="Weekly team sync" required>
                    </div>
                    
                    <div class="form-group">
                        <label>Date</label>
                        <input type="date" id="meetingDate" required>
                    </div>
                    
                    <div class="form-group">
                        <label>Meeting Notes</label>
                        <textarea id="meetingNotes" placeholder="Key discussion points, decisions made, etc." required></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label>Attendees (comma separated)</label>
                        <input type="text" id="meetingAttendees" placeholder="John Doe, Jane Smith, Mike Johnson">
                    </div>
                    
                    <div class="form-group">
                        <label>Action Items (comma separated)</label>
                        <input type="text" id="meetingActions" placeholder="Review Q4 budget, Schedule client call, Update project timeline">
                    </div>
                    
                    <button type="submit">Save Meeting Notes</button>
                </form>
                
                <div class="item-list">
                    <h3>Recent Meetings</h3>
                    <div id="meetingsList"></div>
                </div>
            </div>

            <!-- Task Tracking Panel -->
            <div class="panel">
                <h2>✅ Task Tracking</h2>
                
                <form id="taskForm">
                    <div class="form-group">
                        <label>Task Title</label>
                        <input type="text" id="taskTitle" placeholder="Update project documentation" required>
                    </div>
                    
                    <div class="form-group">
                        <label>Description</label>
                        <textarea id="taskDescription" placeholder="Detailed description of the task..."></textarea>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div class="form-group">
                            <label>Priority</label>
                            <select id="taskPriority">
                                <option value="low">Low</option>
                                <option value="medium" selected>Medium</option>
                                <option value="high">High</option>
                                <option value="urgent">Urgent</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label>Status</label>
                            <select id="taskStatus">
                                <option value="todo" selected>To Do</option>
                                <option value="in_progress">In Progress</option>
                                <option value="done">Done</option>
                                <option value="cancelled">Cancelled</option>
                            </select>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div class="form-group">
                            <label>Due Date</label>
                            <input type="date" id="taskDueDate">
                        </div>
                        
                        <div class="form-group">
                            <label>Assigned To</label>
                            <input type="text" id="taskAssignee" placeholder="Team member name">
                        </div>
                    </div>
                    
                    <button type="submit">Create Task</button>
                </form>
                
                <div class="item-list">
                    <h3>Active Tasks</h3>
                    <div id="tasksList"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Set today's date as default
        document.getElementById('meetingDate').value = new Date().toISOString().split('T')[0];

        // Load data on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadMeetings();
            loadTasks();
            loadStats();
        });

        // Meeting form submission
        document.getElementById('meetingForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const title = document.getElementById('meetingTitle').value;
            const notes = document.getElementById('meetingNotes').value;
            const date = document.getElementById('meetingDate').value;
            const attendeesStr = document.getElementById('meetingAttendees').value;
            const actionsStr = document.getElementById('meetingActions').value;
            
            const attendees = attendeesStr ? attendeesStr.split(',').map(s => s.trim()).filter(s => s) : [];
            const action_items = actionsStr ? actionsStr.split(',').map(s => s.trim()).filter(s => s) : [];
            
            try {
                const response = await fetch('/api/meetings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, notes, date, attendees, action_items })
                });
                
                if (response.ok) {
                    document.getElementById('meetingForm').reset();
                    document.getElementById('meetingDate').value = new Date().toISOString().split('T')[0];
                    loadMeetings();
                    loadStats();
                }
            } catch (error) {
                console.error('Error creating meeting:', error);
            }
        });

        // Task form submission
        document.getElementById('taskForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const title = document.getElementById('taskTitle').value;
            const description = document.getElementById('taskDescription').value;
            const priority = document.getElementById('taskPriority').value;
            const status = document.getElementById('taskStatus').value;
            const due_date = document.getElementById('taskDueDate').value || null;
            const assigned_to = document.getElementById('taskAssignee').value || null;
            
            try {
                const response = await fetch('/api/tasks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, description, priority, status, due_date, assigned_to })
                });
                
                if (response.ok) {
                    document.getElementById('taskForm').reset();
                    document.getElementById('taskPriority').value = 'medium';
                    document.getElementById('taskStatus').value = 'todo';
                    loadTasks();
                    loadStats();
                }
            } catch (error) {
                console.error('Error creating task:', error);
            }
        });

        async function loadMeetings() {
            try {
                const response = await fetch('/api/meetings');
                const meetings = await response.json();
                
                const list = document.getElementById('meetingsList');
                
                if (meetings.length === 0) {
                    list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📭</div><p>No meetings recorded yet</p></div>';
                    return;
                }
                
                list.innerHTML = meetings.map(meeting => `
                    <div class="meeting-item">
                        <h4>${meeting.title}</h4>
                        <div class="meeting-date">📅 ${new Date(meeting.date).toLocaleDateString()}</div>
                        <p>${meeting.notes.substring(0, 150)}${meeting.notes.length > 150 ? '...' : ''}</p>
                        ${meeting.attendees.length > 0 ? `
                            <div class="attendees-list">
                                ${meeting.attendees.map(attendee => `<span class="attendee">${attendee}</span>`).join('')}
                            </div>
                        ` : ''}
                        ${meeting.action_items.length > 0 ? `
                            <div class="action-items">
                                ${meeting.action_items.map(item => `<div class="action-item">⚡ ${item}</div>`).join('')}
                            </div>
                        ` : ''}
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error loading meetings:', error);
            }
        }

        async function loadTasks() {
            try {
                const response = await fetch('/api/tasks');
                const tasks = await response.json();
                
                const list = document.getElementById('tasksList');
                
                if (tasks.length === 0) {
                    list.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><p>No tasks created yet</p></div>';
                    return;
                }
                
                list.innerHTML = tasks.map(task => `
                    <div class="task-item">
                        <h4>${task.title}</h4>
                        <p>${task.description}</p>
                        <div class="task-meta">
                            <span class="badge priority-${task.priority}">
                                ${task.priority.charAt(0).toUpperCase() + task.priority.slice(1)}
                            </span>
                            <span class="badge status-${task.status}">
                                ${task.status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </span>
                            ${task.due_date ? `<span class="badge">📅 ${new Date(task.due_date).toLocaleDateString()}</span>` : ''}
                            ${task.assigned_to ? `<span class="badge">👤 ${task.assigned_to}</span>` : ''}
                        </div>
                        ${task.status !== 'done' && task.status !== 'cancelled' ? `
                            <div style="margin-top: 12px;">
                                <button class="btn-success" onclick="markTaskDone('${task.id}')">Mark Done</button>
                                <button class="btn-secondary" onclick="markTaskProgress('${task.id}')">In Progress</button>
                            </div>
                        ` : ''}
                    </div>
                `).join('');
            } catch (error) {
                console.error('Error loading tasks:', error);
            }
        }

        async function loadStats() {
            try {
                const [meetingsResponse, tasksResponse] = await Promise.all([
                    fetch('/api/meetings'),
                    fetch('/api/tasks')
                ]);
                
                const meetings = await meetingsResponse.json();
                const tasks = await tasksResponse.json();
                
                document.getElementById('meetingCount').textContent = meetings.length;
                document.getElementById('taskCount').textContent = tasks.filter(t => t.status !== 'done' && t.status !== 'cancelled').length;
                document.getElementById('completedCount').textContent = tasks.filter(t => t.status === 'done').length;
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        async function markTaskDone(taskId) {
            try {
                const response = await fetch(`/api/tasks/${taskId}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: 'done' })
                });
                
                if (response.ok) {
                    loadTasks();
                    loadStats();
                }
            } catch (error) {
                console.error('Error updating task:', error);
            }
        }

        async function markTaskProgress(taskId) {
            try {
                const response = await fetch(`/api/tasks/${taskId}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: 'in_progress' })
                });
                
                if (response.ok) {
                    loadTasks();
                    loadStats();
                }
            } catch (error) {
                console.error('Error updating task:', error);
            }
        }
    </script>
</body>
</html>
'''

# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def get_web_interface():
    """Serve web interface"""
    backend.metrics["requests_served"] += 1
    return WEB_INTERFACE

@app.post("/api/meetings")
async def create_meeting(meeting: MeetingNote):
    """Create new meeting note"""
    backend.metrics["requests_served"] += 1
    return await backend.create_meeting(meeting)

@app.get("/api/meetings")
async def get_meetings(limit: int = 50, offset: int = 0):
    """Get meeting notes"""
    backend.metrics["requests_served"] += 1
    return await backend.get_meetings(limit, offset)

@app.post("/api/tasks")
async def create_task(task: Task):
    """Create new task"""
    backend.metrics["requests_served"] += 1
    return await backend.create_task(task)

@app.get("/api/tasks")
async def get_tasks(status: Optional[str] = None, limit: int = 100, offset: int = 0):
    """Get tasks"""
    backend.metrics["requests_served"] += 1
    return await backend.get_tasks(status, limit, offset)

@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, updates: Dict[str, Any]):
    """Update task"""
    backend.metrics["requests_served"] += 1
    success = await backend.update_task(task_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "BusinessLog",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/metrics")
async def get_metrics():
    """Get service metrics"""
    return {
        "service": "BusinessLog",
        "status": "healthy",
        "metrics": backend.metrics,
        "database": {
            "path": str(backend.db_path),
            "exists": backend.db_path.exists(),
            "size_mb": round(backend.db_path.stat().st_size / (1024*1024), 2) if backend.db_path.exists() else 0
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="BusinessLog Service")
    parser.add_argument("--port", type=int, default=8003, help="Port to run the service on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    
    args = parser.parse_args()
    
    print("🏢 Starting BusinessLog Service")
    print(f"📝 Meeting notes and task tracking")
    print(f"✅ Professional business productivity")
    print(f"🌐 Running on http://{args.host}:{args.port}")
    
    uvicorn.run(
        "business_logger:app",
        host=args.host,
        port=args.port,
        reload=False,
        access_log=True
    )