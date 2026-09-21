"""
Command Line Interface for Unified Agent Backend

Provides CLI commands for managing the application, database, and other utilities.
"""

import typer
from typing import Optional
import sys

app = typer.Typer(
    name="unified-agent",
    help="Unified Agent Backend CLI",
    add_completion=False,
)


@app.command()
def version():
    """Show version information."""
    from app import __version__
    typer.echo(f"Unified Agent Backend v{__version__}")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
    workers: int = typer.Option(1, help="Number of worker processes"),
):
    """Start the FastAPI server."""
    import uvicorn

    if reload:
        typer.echo("Starting server with auto-reload...")
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=True,
        )
    else:
        typer.echo(f"Starting server on {host}:{port} with {workers} workers...")
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            workers=workers,
        )


@app.command()
def migrate(
    revision: str = typer.Option("head", help="Revision to migrate to"),
    downgrade: bool = typer.Option(False, help="Downgrade instead of upgrade"),
):
    """Run database migrations."""
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")

    if downgrade:
        typer.echo(f"Downgrading to revision: {revision}")
        command.downgrade(alembic_cfg, revision)
    else:
        typer.echo(f"Migrating to revision: {revision}")
        command.upgrade(alembic_cfg, revision)

    typer.echo("Migration completed successfully!")


@app.command()
def create_migration(
    message: str = typer.Argument(..., help="Migration message"),
    autogenerate: bool = typer.Option(True, help="Auto-generate migration from models"),
):
    """Create a new database migration."""
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config("alembic.ini")

    if autogenerate:
        typer.echo(f"Creating auto-generated migration: {message}")
        command.revision(alembic_cfg, autogenerate=True, message=message)
    else:
        typer.echo(f"Creating empty migration: {message}")
        command.revision(alembic_cfg, message=message)

    typer.echo("Migration created successfully!")


@app.command()
def shell():
    """Start an interactive shell with app context."""
    try:
        from IPython import embed
        embed(banner1="Unified Agent Backend Shell")
    except ImportError:
        import code
        code.interact(banner="Unified Agent Backend Shell")


@app.command()
def test(
    path: str = typer.Option("src/tests/", help="Test path"),
    verbose: bool = typer.Option(False, help="Verbose output"),
    coverage: bool = typer.Option(True, help="Generate coverage report"),
):
    """Run the test suite."""
    import subprocess

    cmd = ["pytest", path]
    if verbose:
        cmd.append("-v")
    if coverage:
        cmd.extend(["--cov=src/app", "--cov-report=term-missing"])

    typer.echo(f"Running tests: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


@app.command()
def lint(
    fix: bool = typer.Option(False, help="Fix linting issues automatically"),
):
    """Run code linting."""
    import subprocess

    cmd = ["ruff", "check", "src/"]
    if fix:
        cmd.append("--fix")

    typer.echo(f"Running linting: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


@app.command()
def format_code():
    """Format code with black and ruff."""
    import subprocess

    typer.echo("Formatting code with black...")
    subprocess.run(["black", "src/"])

    typer.echo("Sorting imports with ruff...")
    subprocess.run(["ruff", "format", "src/"])

    typer.echo("Code formatting completed!")


@app.command()
def health_check():
    """Check the health of the application and its dependencies."""
    import asyncio
    import httpx

    async def check_health():
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:8000/health")
                if response.status_code == 200:
                    typer.echo("✅ Application is healthy")
                    typer.echo(f"Response: {response.json()}")
                else:
                    typer.echo(f"❌ Application returned status {response.status_code}")
            except httpx.ConnectError:
                typer.echo("❌ Cannot connect to application")

    asyncio.run(check_health())


if __name__ == "__main__":
    app()