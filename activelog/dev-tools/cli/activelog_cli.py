#!/usr/bin/env python3
"""
ActiveLog Development CLI Tool
Provides common operations for service management, data seeding, and development tasks.
"""

import os
import sys
import json
import subprocess
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
import click
import yaml
import psutil
import docker
import requests
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logger = logging.getLogger(__name__)


class ActiveLogCLI:
    """Main CLI class for ActiveLog development operations."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.docker_client = None
        self.config = self._load_config()
        
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"Docker client not available: {e}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load CLI configuration."""
        config_file = self.project_root / "dev-tools" / "cli" / "config.yml"
        
        if config_file.exists():
            with open(config_file) as f:
                return yaml.safe_load(f)
        
        # Default configuration
        return {
            'services': {
                'api_gateway': {'port': 8000, 'path': 'api_gateway'},
                'auth_service': {'port': 8001, 'path': 'services/auth'},
                'file_sync': {'port': 8002, 'path': 'services/file_sync'},
                'ai_orchestrator': {'port': 8003, 'path': 'services/ai_orchestrator'},
                'metadata_service': {'port': 8004, 'path': 'services/metadata'},
                'analytics_service': {'port': 8005, 'path': 'services/analytics'},
            },
            'databases': {
                'postgres': {'port': 5432, 'container': 'activelog-postgres'},
                'redis': {'port': 6379, 'container': 'activelog-redis'},
                'elasticsearch': {'port': 9200, 'container': 'activelog-elasticsearch'}
            },
            'external_services': {
                'nginx': {'port': 80, 'container': 'activelog-nginx'},
                'monitoring': {'port': 3000, 'container': 'activelog-grafana'}
            }
        }


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--config', '-c', help='Configuration file path')
@click.pass_context
def cli(ctx, verbose, config):
    """ActiveLog Development CLI - Manage services, data, and development tasks."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['config_file'] = config
    
    # Setup logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    ctx.obj['cli'] = ActiveLogCLI()


@cli.group()
def services():
    """Service management commands."""
    pass


@services.command()
@click.argument('service_name', required=False)
@click.option('--all', '-a', is_flag=True, help='Start all services')
@click.option('--docker', '-d', is_flag=True, help='Use Docker containers')
@click.option('--detached', is_flag=True, help='Run in background')
@click.pass_context
def start(ctx, service_name, all, docker, detached):
    """Start one or more services."""
    cli_obj = ctx.obj['cli']
    
    if docker:
        _start_services_docker(cli_obj, service_name, all, detached)
    else:
        _start_services_local(cli_obj, service_name, all, detached)


@services.command()
@click.argument('service_name', required=False)
@click.option('--all', '-a', is_flag=True, help='Stop all services')
@click.option('--docker', '-d', is_flag=True, help='Use Docker containers')
@click.pass_context
def stop(ctx, service_name, all, docker):
    """Stop one or more services."""
    cli_obj = ctx.obj['cli']
    
    if docker:
        _stop_services_docker(cli_obj, service_name, all)
    else:
        _stop_services_local(cli_obj, service_name, all)


@services.command()
@click.option('--docker', '-d', is_flag=True, help='Check Docker containers')
@click.pass_context
def status(ctx, docker):
    """Check status of all services."""
    cli_obj = ctx.obj['cli']
    
    if docker:
        _show_docker_status(cli_obj)
    else:
        _show_local_status(cli_obj)


@services.command()
@click.argument('service_name')
@click.option('--lines', '-n', default=100, help='Number of log lines')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--docker', '-d', is_flag=True, help='Docker container logs')
@click.pass_context
def logs(ctx, service_name, lines, follow, docker):
    """View service logs."""
    cli_obj = ctx.obj['cli']
    
    if docker:
        _show_docker_logs(cli_obj, service_name, lines, follow)
    else:
        _show_local_logs(cli_obj, service_name, lines, follow)


@cli.group()
def db():
    """Database management commands."""
    pass


@db.command()
@click.option('--reset', is_flag=True, help='Reset database (drop all tables)')
@click.option('--sample-data', is_flag=True, help='Add sample data')
@click.pass_context
def setup(ctx, reset, sample_data):
    """Setup database schema and initial data."""
    cli_obj = ctx.obj['cli']
    
    click.echo("Setting up database...")
    
    if reset:
        if click.confirm("This will drop all tables. Continue?"):
            _reset_database(cli_obj)
    
    _run_migrations(cli_obj)
    
    if sample_data:
        _seed_sample_data(cli_obj)
    
    click.echo("✅ Database setup completed!")


@db.command()
@click.option('--size', default='small', type=click.Choice(['small', 'medium', 'large']))
@click.option('--users', default=10, help='Number of users to create')
@click.option('--files', default=100, help='Number of files to create')
@click.pass_context
def seed(ctx, size, users, files):
    """Seed database with test data."""
    cli_obj = ctx.obj['cli']
    
    click.echo(f"Seeding database with {size} dataset...")
    
    # Adjust numbers based on size
    if size == 'medium':
        users *= 5
        files *= 10
    elif size == 'large':
        users *= 20
        files *= 50
    
    _seed_test_data(cli_obj, users, files)
    
    click.echo(f"✅ Database seeded with {users} users and {files} files!")


@db.command()
@click.pass_context
def migrate(ctx):
    """Run database migrations."""
    cli_obj = ctx.obj['cli']
    
    click.echo("Running database migrations...")
    _run_migrations(cli_obj)
    click.echo("✅ Migrations completed!")


@db.command()
@click.pass_context
def backup(ctx):
    """Create database backup."""
    cli_obj = ctx.obj['cli']
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"backup_{timestamp}.sql"
    
    click.echo(f"Creating backup: {backup_file}")
    _create_backup(cli_obj, backup_file)
    click.echo("✅ Backup created!")


@cli.group()
def dev():
    """Development environment commands."""
    pass


@dev.command()
@click.option('--full', is_flag=True, help='Full environment setup')
@click.option('--docker', is_flag=True, help='Setup with Docker')
@click.pass_context
def setup(ctx, full, docker):
    """Setup development environment."""
    cli_obj = ctx.obj['cli']
    
    click.echo("🚀 Setting up ActiveLog development environment...")
    
    # Run setup script
    setup_script = cli_obj.project_root / "dev-tools" / "setup" / "dev_setup.py"
    
    cmd = [sys.executable, str(setup_script)]
    if full:
        cmd.append('--full')
    if docker:
        cmd.append('--docker')
    
    try:
        subprocess.run(cmd, check=True, cwd=cli_obj.project_root)
        click.echo("✅ Development environment setup completed!")
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Setup failed: {e}")
        sys.exit(1)


@dev.command()
@click.pass_context
def format(ctx):
    """Format code using black, isort, and prettier."""
    cli_obj = ctx.obj['cli']
    
    click.echo("🎨 Formatting code...")
    
    # Run formatting
    format_script = cli_obj.project_root / "dev-tools" / "formatting" / "format_code.py"
    
    try:
        subprocess.run([sys.executable, str(format_script)], check=True, cwd=cli_obj.project_root)
        click.echo("✅ Code formatting completed!")
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Formatting failed: {e}")
        sys.exit(1)


@dev.command()
@click.option('--output', '-o', default='deps.svg', help='Output file')
@click.pass_context
def deps(ctx, output):
    """Generate service dependency visualization."""
    cli_obj = ctx.obj['cli']
    
    click.echo("📊 Generating dependency visualization...")
    
    viz_script = cli_obj.project_root / "dev-tools" / "visualization" / "dependency_visualizer.py"
    
    try:
        subprocess.run([
            sys.executable, str(viz_script), 
            '--output', output
        ], check=True, cwd=cli_obj.project_root)
        click.echo(f"✅ Dependency visualization saved to {output}")
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Visualization generation failed: {e}")
        sys.exit(1)


@cli.group()
def test():
    """Testing commands."""
    pass


@test.command()
@click.option('--service', help='Test specific service')
@click.option('--coverage', is_flag=True, help='Run with coverage')
@click.option('--integration', is_flag=True, help='Run integration tests')
@click.pass_context
def run(ctx, service, coverage, integration):
    """Run tests."""
    cli_obj = ctx.obj['cli']
    
    click.echo("🧪 Running tests...")
    
    cmd = ['python', '-m', 'pytest']
    
    if service:
        if service in cli_obj.config['services']:
            service_path = cli_obj.config['services'][service]['path']
            cmd.append(f"tests/{service_path}")
        else:
            click.echo(f"❌ Unknown service: {service}")
            sys.exit(1)
    
    if coverage:
        cmd.extend(['--cov=.', '--cov-report=html', '--cov-report=term'])
    
    if integration:
        cmd.extend(['-m', 'integration'])
    
    try:
        subprocess.run(cmd, check=True, cwd=cli_obj.project_root)
        click.echo("✅ Tests completed!")
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Tests failed: {e}")
        sys.exit(1)


@test.command()
@click.option('--scenario', default='normal_load', help='Load test scenario')
@click.option('--duration', default='5m', help='Test duration')
@click.pass_context
def load(ctx, scenario, duration):
    """Run load tests."""
    cli_obj = ctx.obj['cli']
    
    click.echo(f"⚡ Running load test: {scenario}")
    
    load_test_script = cli_obj.project_root / "optimizations" / "benchmarks" / "load_testing.py"
    
    cmd = [
        sys.executable, str(load_test_script),
        '--host', 'http://localhost:8000',
        '--scenario', scenario,
        '--headless'
    ]
    
    try:
        subprocess.run(cmd, check=True, cwd=cli_obj.project_root)
        click.echo("✅ Load test completed!")
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Load test failed: {e}")
        sys.exit(1)


@cli.group()
def generate():
    """Code generation commands."""
    pass


@generate.command()
@click.argument('service_name')
@click.option('--template', default='fastapi', help='Service template')
@click.option('--port', help='Service port')
@click.pass_context
def service(ctx, service_name, template, port):
    """Generate a new service."""
    cli_obj = ctx.obj['cli']
    
    click.echo(f"🏗️  Generating service: {service_name}")
    
    gen_script = cli_obj.project_root / "dev-tools" / "templates" / "generate_service.py"
    
    cmd = [
        sys.executable, str(gen_script),
        '--name', service_name,
        '--template', template
    ]
    
    if port:
        cmd.extend(['--port', port])
    
    try:
        subprocess.run(cmd, check=True, cwd=cli_obj.project_root)
        click.echo(f"✅ Service {service_name} generated!")
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Service generation failed: {e}")
        sys.exit(1)


@cli.group()
def logs():
    """Log management commands."""
    pass


@logs.command()
@click.option('--service', help='Filter by service')
@click.option('--level', help='Filter by log level')
@click.option('--since', help='Show logs since timestamp')
@click.option('--follow', '-f', is_flag=True, help='Follow logs')
@click.pass_context
def search(ctx, service, level, since, follow):
    """Search and filter logs."""
    cli_obj = ctx.obj['cli']
    
    click.echo("🔍 Searching logs...")
    
    log_tool = cli_obj.project_root / "dev-tools" / "logging" / "log_aggregator.py"
    
    cmd = [sys.executable, str(log_tool), 'search']
    
    if service:
        cmd.extend(['--service', service])
    if level:
        cmd.extend(['--level', level])
    if since:
        cmd.extend(['--since', since])
    if follow:
        cmd.append('--follow')
    
    try:
        subprocess.run(cmd, check=True, cwd=cli_obj.project_root)
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Log search failed: {e}")
        sys.exit(1)


@cli.group()
def profile():
    """Performance profiling commands."""
    pass


@profile.command()
@click.argument('service_name')
@click.option('--duration', default=30, help='Profile duration in seconds')
@click.option('--output', help='Output file')
@click.pass_context
def service(ctx, service_name, duration, output):
    """Profile a service."""
    cli_obj = ctx.obj['cli']
    
    click.echo(f"📊 Profiling service: {service_name}")
    
    profiler = cli_obj.project_root / "dev-tools" / "profiling" / "service_profiler.py"
    
    cmd = [
        sys.executable, str(profiler),
        '--service', service_name,
        '--duration', str(duration)
    ]
    
    if output:
        cmd.extend(['--output', output])
    
    try:
        subprocess.run(cmd, check=True, cwd=cli_obj.project_root)
        click.echo("✅ Profiling completed!")
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Profiling failed: {e}")
        sys.exit(1)


# Helper functions for service management
def _start_services_docker(cli_obj, service_name, all_services, detached):
    """Start services using Docker."""
    if not cli_obj.docker_client:
        click.echo("❌ Docker client not available")
        return
    
    compose_file = cli_obj.project_root / "docker-compose.dev.yml"
    
    cmd = ['docker-compose', '-f', str(compose_file), 'up']
    
    if detached:
        cmd.append('-d')
    
    if service_name and not all_services:
        cmd.append(service_name)
    
    subprocess.run(cmd, cwd=cli_obj.project_root)


def _start_services_local(cli_obj, service_name, all_services, detached):
    """Start services locally."""
    services = cli_obj.config['services']
    
    if all_services:
        for name, config in services.items():
            _start_single_service(cli_obj, name, config, detached)
    elif service_name:
        if service_name in services:
            _start_single_service(cli_obj, service_name, services[service_name], detached)
        else:
            click.echo(f"❌ Unknown service: {service_name}")
    else:
        click.echo("Please specify a service name or use --all")


def _start_single_service(cli_obj, name, config, detached):
    """Start a single service locally."""
    service_path = cli_obj.project_root / config['path']
    port = config['port']
    
    click.echo(f"Starting {name} on port {port}...")
    
    # Check if service is already running
    if _is_port_in_use(port):
        click.echo(f"⚠️  Port {port} is already in use")
        return
    
    # Start service
    cmd = [sys.executable, '-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', str(port)]
    
    if detached:
        subprocess.Popen(cmd, cwd=service_path)
        click.echo(f"✅ {name} started in background")
    else:
        subprocess.run(cmd, cwd=service_path)


def _stop_services_docker(cli_obj, service_name, all_services):
    """Stop services using Docker."""
    compose_file = cli_obj.project_root / "docker-compose.dev.yml"
    
    cmd = ['docker-compose', '-f', str(compose_file), 'down']
    
    if service_name and not all_services:
        cmd = ['docker-compose', '-f', str(compose_file), 'stop', service_name]
    
    subprocess.run(cmd, cwd=cli_obj.project_root)


def _stop_services_local(cli_obj, service_name, all_services):
    """Stop services locally."""
    services = cli_obj.config['services']
    
    if all_services:
        for name, config in services.items():
            _stop_single_service(name, config['port'])
    elif service_name:
        if service_name in services:
            _stop_single_service(service_name, services[service_name]['port'])
        else:
            click.echo(f"❌ Unknown service: {service_name}")
    else:
        click.echo("Please specify a service name or use --all")


def _stop_single_service(name, port):
    """Stop a single service by port."""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            for conn in proc.info['connections']:
                if conn.laddr.port == port:
                    proc.terminate()
                    click.echo(f"✅ Stopped {name} (PID: {proc.pid})")
                    return
        
        click.echo(f"⚠️  No process found on port {port}")
    except Exception as e:
        click.echo(f"❌ Error stopping {name}: {e}")


def _show_docker_status(cli_obj):
    """Show Docker container status."""
    if not cli_obj.docker_client:
        click.echo("❌ Docker client not available")
        return
    
    containers = cli_obj.docker_client.containers.list(all=True)
    
    click.echo("\n📊 Docker Container Status:")
    click.echo("-" * 80)
    
    for container in containers:
        if 'activelog' in container.name:
            status = "🟢 Running" if container.status == 'running' else "🔴 Stopped"
            ports = ", ".join([f"{p['PublicPort']}:{p['PrivatePort']}" for p in container.ports.values() if p])
            
            click.echo(f"{container.name:<25} {status:<12} {ports}")


def _show_local_status(cli_obj):
    """Show local service status."""
    services = cli_obj.config['services']
    
    click.echo("\n📊 Local Service Status:")
    click.echo("-" * 60)
    
    for name, config in services.items():
        port = config['port']
        status = "🟢 Running" if _is_port_in_use(port) else "🔴 Stopped"
        
        click.echo(f"{name:<25} {status:<12} Port: {port}")


def _show_docker_logs(cli_obj, service_name, lines, follow):
    """Show Docker container logs."""
    if not cli_obj.docker_client:
        click.echo("❌ Docker client not available")
        return
    
    try:
        container = cli_obj.docker_client.containers.get(f"activelog-{service_name}")
        
        if follow:
            for line in container.logs(stream=True, tail=lines):
                click.echo(line.decode().strip())
        else:
            logs = container.logs(tail=lines).decode()
            click.echo(logs)
            
    except Exception as e:
        click.echo(f"❌ Error getting logs: {e}")


def _show_local_logs(cli_obj, service_name, lines, follow):
    """Show local service logs."""
    log_file = cli_obj.project_root / "logs" / f"{service_name}.log"
    
    if not log_file.exists():
        click.echo(f"❌ Log file not found: {log_file}")
        return
    
    if follow:
        subprocess.run(['tail', '-f', '-n', str(lines), str(log_file)])
    else:
        subprocess.run(['tail', '-n', str(lines), str(log_file)])


def _is_port_in_use(port):
    """Check if a port is in use."""
    for conn in psutil.net_connections():
        if conn.laddr.port == port:
            return True
    return False


def _reset_database(cli_obj):
    """Reset database by dropping all tables."""
    # This would connect to the database and drop all tables
    click.echo("🗑️  Dropping all database tables...")
    # Implementation would depend on your database setup


def _run_migrations(cli_obj):
    """Run database migrations."""
    # Run Alembic migrations
    subprocess.run(['alembic', 'upgrade', 'head'], cwd=cli_obj.project_root)


def _seed_sample_data(cli_obj):
    """Seed database with sample data."""
    click.echo("🌱 Seeding sample data...")
    # Implementation would use your data seeding logic


def _seed_test_data(cli_obj, users, files):
    """Seed database with test data."""
    click.echo(f"🌱 Seeding {users} users and {files} files...")
    # Implementation would use your test data generation logic


def _create_backup(cli_obj, backup_file):
    """Create database backup."""
    # Use pg_dump or similar
    subprocess.run([
        'pg_dump', 
        '-h', 'localhost',
        '-U', 'activelog',
        '-d', 'activelog',
        '-f', backup_file
    ])


if __name__ == '__main__':
    cli()