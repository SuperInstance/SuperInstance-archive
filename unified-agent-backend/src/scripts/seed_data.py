#!/usr/bin/env python3
"""
Database seeding script.

This script seeds the database with sample data for development and testing.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config.settings import settings
from app.models import Agent, Workflow, Tool, AgentTool

# Database setup
DATABASE_URL = getattr(settings, 'database_url',
    os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/unified_agent_db"))

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_sample_agents() -> list[Agent]:
    """Create sample agents."""
    agents = [
        Agent(
            name="Chat Assistant",
            description="General purpose chat assistant for conversations and Q&A",
            agent_type="chat",
            status="active",
            is_active=True,
            is_public=True,
            config={"model": "gpt-3.5-turbo", "temperature": 0.7, "max_tokens": 1000},
            capabilities=["text_generation", "conversation"],
            max_concurrent_tasks=5,
            timeout_seconds=60,
            tags=["chat", "ai", "conversation"],
        ),
        Agent(
            name="Code Reviewer",
            description="AI agent specialized in code review and analysis",
            agent_type="specialized",
            status="active",
            is_active=True,
            is_public=True,
            config={"model": "gpt-4", "focus": "code_quality", "languages": ["python", "javascript", "java"]},
            capabilities=["code_generation", "code_analysis", "text_generation"],
            max_concurrent_tasks=3,
            timeout_seconds=120,
            tags=["code", "review", "analysis", "ai"],
        ),
        Agent(
            name="Data Analyst",
            description="Agent for data analysis and visualization tasks",
            agent_type="task",
            status="active",
            is_active=True,
            is_public=True,
            config={"libraries": ["pandas", "numpy", "matplotlib"], "max_data_size_mb": 100},
            capabilities=["data_analysis", "file_management", "visualization"],
            max_concurrent_tasks=2,
            timeout_seconds=180,
            tags=["data", "analysis", "visualization"],
        ),
        Agent(
            name="Workflow Coordinator",
            description="Coordinates and manages complex workflow executions",
            agent_type="coordinator",
            status="active",
            is_active=True,
            is_public=False,
            config={"max_workflows": 10, "timeout_minutes": 30},
            capabilities=["workflow_management", "scheduling", "monitoring"],
            max_concurrent_tasks=10,
            timeout_seconds=1800,
            tags=["workflow", "coordination", "management"],
        ),
    ]

    return agents


async def create_sample_workflows() -> list[Workflow]:
    """Create sample workflows."""
    workflows = [
        Workflow(
            name="Document Processing Pipeline",
            description="Process uploaded documents, extract text, and analyze content",
            version="1.0.0",
            status="active",
            is_active=True,
            is_template=True,
            definition={
                "nodes": [
                    {
                        "id": "upload_trigger",
                        "type": "trigger",
                        "name": "Document Upload",
                        "config": {"file_types": ["pdf", "docx", "txt"]}
                    },
                    {
                        "id": "extract_text",
                        "type": "agent_task",
                        "name": "Extract Text",
                        "config": {"agent_type": "document_processor"}
                    },
                    {
                        "id": "analyze_content",
                        "type": "agent_task",
                        "name": "Analyze Content",
                        "config": {"agent_type": "data_analyst"}
                    },
                    {
                        "id": "save_results",
                        "type": "sink",
                        "name": "Save Results",
                        "config": {"output_format": "json"}
                    }
                ],
                "edges": [
                    {"source": "upload_trigger", "target": "extract_text"},
                    {"source": "extract_text", "target": "analyze_content"},
                    {"source": "analyze_content", "target": "save_results"}
                ]
            },
            config={"timeout_minutes": 15, "retry_attempts": 3},
            timeout_seconds=900,
            max_retries=3,
            template_category="document_processing",
            template_tags=["document", "processing", "analysis"],
        ),
        Workflow(
            name="Customer Support Response",
            description="Generate automated customer support responses based on tickets",
            version="1.0.0",
            status="active",
            is_active=True,
            is_template=True,
            definition={
                "nodes": [
                    {
                        "id": "ticket_received",
                        "type": "trigger",
                        "name": "Support Ticket",
                        "config": {"priority": ["high", "medium", "low"]}
                    },
                    {
                        "id": "classify_ticket",
                        "type": "agent_task",
                        "name": "Classify Ticket",
                        "config": {"agent_type": "classifier"}
                    },
                    {
                        "id": "generate_response",
                        "type": "agent_task",
                        "name": "Generate Response",
                        "config": {"agent_type": "chat_assistant"}
                    },
                    {
                        "id": "send_response",
                        "type": "webhook",
                        "name": "Send Response",
                        "config": {"endpoint": "/api/support/respond"}
                    }
                ],
                "edges": [
                    {"source": "ticket_received", "target": "classify_ticket"},
                    {"source": "classify_ticket", "target": "generate_response"},
                    {"source": "generate_response", "target": "send_response"}
                ]
            },
            config={"response_time_minutes": 5, "escalation_enabled": True},
            timeout_seconds=300,
            max_retries=2,
            template_category="customer_support",
            template_tags=["support", "automation", "response"],
        ),
        Workflow(
            name="Code Quality Check",
            description="Automated code quality checks and analysis for pull requests",
            version="1.0.0",
            status="active",
            is_active=True,
            is_template=False,
            definition={
                "nodes": [
                    {
                        "id": "pr_trigger",
                        "type": "trigger",
                        "name": "Pull Request",
                        "config": {"event": "pull_request.opened"}
                    },
                    {
                        "id": "analyze_code",
                        "type": "agent_task",
                        "name": "Code Analysis",
                        "config": {"agent_type": "code_reviewer"}
                    },
                    {
                        "id": "run_tests",
                        "type": "script",
                        "name": "Run Tests",
                        "config": {"command": "pytest", "timeout": 300}
                    },
                    {
                        "id": "check_security",
                        "type": "agent_task",
                        "name": "Security Scan",
                        "config": {"tools": ["bandit", "safety"]}
                    },
                    {
                        "id": "report_results",
                        "type": "sink",
                        "name": "Report Results",
                        "config": {"format": "github_comment"}
                    }
                ],
                "edges": [
                    {"source": "pr_trigger", "target": "analyze_code"},
                    {"source": "analyze_code", "target": "run_tests"},
                    {"source": "run_tests", "target": "check_security"},
                    {"source": "check_security", "target": "report_results"}
                ]
            },
            config={"fail_on_error": True, "notify_on_failure": True},
            timeout_seconds=600,
            max_retries=1,
            tags=["code", "quality", "ci/cd"],
        ),
    ]

    return workflows


async def assign_tools_to_agents(session: AsyncSession, agents: list[Agent], tools: list[Tool]) -> list[AgentTool]:
    """Assign tools to agents based on their capabilities."""
    assignments = []

    # Get tools by name for easier access
    tool_map = {tool.name: tool for tool in tools}

    for agent in agents:
        if "Chat Assistant" in agent.name:
            # Chat Assistant gets text generation and web search
            for tool_name in ["Text Generation", "Web Search", "Email Sender"]:
                if tool_name in tool_map:
                    assignments.append(AgentTool(
                        agent_id=agent.id,
                        tool_id=tool_map[tool_name].id,
                        status="active",
                        is_enabled=True,
                        can_execute=True,
                        max_executions_per_day=100,
                        assigned_by=uuid4(),
                        notes="Auto-assigned based on agent capabilities"
                    ))

        elif "Code Reviewer" in agent.name:
            # Code Reviewer gets code generation and database query tools
            for tool_name in ["Code Generation", "Database Query", "API Caller"]:
                if tool_name in tool_map:
                    assignments.append(AgentTool(
                        agent_id=agent.id,
                        tool_id=tool_map[tool_name].id,
                        status="active",
                        is_enabled=True,
                        can_execute=True,
                        max_executions_per_day=50,
                        assigned_by=uuid4(),
                        notes="Auto-assigned based on agent capabilities"
                    ))

        elif "Data Analyst" in agent.name:
            # Data Analyst gets data analysis, file operations, and database tools
            for tool_name in ["Data Analysis", "File Operations", "Database Query", "Image Processing"]:
                if tool_name in tool_map:
                    assignments.append(AgentTool(
                        agent_id=agent.id,
                        tool_id=tool_map[tool_name].id,
                        status="active",
                        is_enabled=True,
                        can_execute=True,
                        max_executions_per_day=30,
                        max_file_size_mb=100,
                        assigned_by=uuid4(),
                        notes="Auto-assigned based on agent capabilities"
                    ))

        elif "Workflow Coordinator" in agent.name:
            # Workflow Coordinator gets API caller and file operations for orchestration
            for tool_name in ["API Caller", "File Operations", "Email Sender"]:
                if tool_name in tool_map:
                    assignments.append(AgentTool(
                        agent_id=agent.id,
                        tool_id=tool_map[tool_name].id,
                        status="active",
                        is_enabled=True,
                        can_execute=True,
                        max_executions_per_day=200,
                        assigned_by=uuid4(),
                        notes="Auto-assigned based on agent capabilities"
                    ))

    return assignments


async def seed_database():
    """Seed the database with sample data."""
    async with async_session() as session:
        try:
            print("Starting database seeding...")

            # Check if tools already exist
            existing_tools = await session.execute("SELECT COUNT(*) FROM tools")
            tool_count = existing_tools.scalar()

            if tool_count == 0:
                print("Error: No tools found in database. Please run migrations first.")
                return

            # Create sample agents
            print("Creating sample agents...")
            agents = create_sample_agents()
            for agent in agents:
                session.add(agent)
            await session.commit()
            print(f"Created {len(agents)} agents")

            # Create sample workflows
            print("Creating sample workflows...")
            workflows = create_sample_workflows()
            for workflow in workflows:
                session.add(workflow)
            await session.commit()
            print(f"Created {len(workflows)} workflows")

            # Get all tools for assignments
            tools_result = await session.execute("SELECT * FROM tools")
            tools = [Tool(**row._asdict()) for row in tools_result.fetchall()]
            print(f"Found {len(tools)} tools in database")

            # Assign tools to agents
            print("Assigning tools to agents...")
            assignments = await assign_tools_to_agents(session, agents, tools)
            for assignment in assignments:
                session.add(assignment)
            await session.commit()
            print(f"Created {len(assignments)} agent-tool assignments")

            print("Database seeding completed successfully!")

        except Exception as e:
            print(f"Error during database seeding: {e}")
            await session.rollback()
            raise


async def main():
    """Main function."""
    try:
        await seed_database()
    except Exception as e:
        print(f"Seeding failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())