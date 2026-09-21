#!/usr/bin/env python3
"""
ActiveLog Plugin Executor - Sandboxed execution environment
"""

import asyncio
import json
import logging
import os
import resource
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import docker
import psutil
from dataclasses import dataclass


@dataclass
class ResourceLimits:
    cpu_shares: int = 512  # 0.5 CPU
    memory_limit: str = "256m"
    disk_limit: str = "100m"
    timeout_seconds: int = 60
    network_enabled: bool = False
    filesystem_read: List[str] = None
    filesystem_write: List[str] = None
    temp_access: bool = True


@dataclass
class PluginExecution:
    plugin_id: str
    runtime_type: str
    code_path: str
    manifest: Dict[str, Any]
    config: Dict[str, Any]
    limits: ResourceLimits
    context: Dict[str, Any]


class PluginSandbox:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.active_containers = {}
        self.logger = logging.getLogger(__name__)
        
    async def execute_plugin(self, execution: PluginExecution) -> Dict[str, Any]:
        """Execute plugin in sandboxed environment"""
        container = None
        
        try:
            # Create container with resource limits
            container = await self._create_container(execution)
            
            # Start execution
            start_time = time.time()
            container.start()
            
            # Monitor execution
            result = await self._monitor_execution(container, execution, start_time)
            
            return {
                'success': True,
                'result': result,
                'execution_time': time.time() - start_time
            }
            
        except Exception as e:
            self.logger.error(f"Plugin execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'execution_time': time.time() - start_time if 'start_time' in locals() else 0
            }
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup container: {e}")
    
    async def _create_container(self, execution: PluginExecution) -> docker.models.containers.Container:
        """Create Docker container with security constraints"""
        limits = execution.limits
        
        # Determine base image
        if execution.runtime_type == 'typescript':
            image = 'activelog/plugin-runtime:node'
        elif execution.runtime_type == 'python':
            image = 'activelog/plugin-runtime:python'
        elif execution.runtime_type == 'wasm':
            image = 'activelog/plugin-runtime:wasm'
        else:
            raise ValueError(f"Unsupported runtime: {execution.runtime_type}")
        
        # Security constraints
        security_opt = [
            'no-new-privileges:true',
            'seccomp:unconfined'  # May need custom seccomp profile
        ]
        
        # Network configuration
        network_mode = 'bridge' if limits.network_enabled else 'none'
        
        # Volume mounts
        volumes = {}
        
        # Add plugin code
        volumes[execution.code_path] = {'bind': '/app/plugin', 'mode': 'ro'}
        
        # Add temp directory if allowed
        if limits.temp_access:
            temp_dir = tempfile.mkdtemp()
            volumes[temp_dir] = {'bind': '/tmp/plugin', 'mode': 'rw'}
        
        # Add read-only filesystem mounts
        if limits.filesystem_read:
            for path in limits.filesystem_read:
                if os.path.exists(path):
                    volumes[path] = {'bind': f'/mnt/ro/{Path(path).name}', 'mode': 'ro'}
        
        # Add read-write filesystem mounts
        if limits.filesystem_write:
            for path in limits.filesystem_write:
                if os.path.exists(path):
                    volumes[path] = {'bind': f'/mnt/rw/{Path(path).name}', 'mode': 'rw'}
        
        # Environment variables
        environment = {
            'PLUGIN_ID': execution.plugin_id,
            'PLUGIN_CONFIG': json.dumps(execution.config),
            'PLUGIN_CONTEXT': json.dumps(execution.context),
            'PLUGIN_MANIFEST': json.dumps(execution.manifest),
            'NODE_ENV': 'production',
            'PYTHONPATH': '/app/plugin'
        }
        
        # Resource limits
        cpu_period = 100000  # 100ms
        cpu_quota = int(cpu_period * (limits.cpu_shares / 1024))  # Convert shares to quota
        
        container = self.docker_client.containers.create(
            image=image,
            command=self._get_runtime_command(execution),
            environment=environment,
            volumes=volumes,
            network_mode=network_mode,
            security_opt=security_opt,
            user='plugin',
            read_only=True,
            tmpfs={
                '/tmp': 'rw,noexec,nosuid,size=100m',
                '/var/tmp': 'rw,noexec,nosuid,size=10m'
            },
            mem_limit=limits.memory_limit,
            cpu_period=cpu_period,
            cpu_quota=cpu_quota,
            pids_limit=50,
            ulimits=[
                docker.types.Ulimit(name='nofile', soft=1024, hard=1024),
                docker.types.Ulimit(name='nproc', soft=50, hard=50)
            ],
            cap_drop=['ALL'],
            cap_add=['CHOWN', 'SETGID', 'SETUID'],  # Minimal capabilities
            detach=True,
            remove=False,  # We'll remove manually after getting logs
            stdin_open=False,
            tty=False
        )
        
        return container
    
    def _get_runtime_command(self, execution: PluginExecution) -> List[str]:
        """Get runtime-specific execution command"""
        if execution.runtime_type == 'typescript':
            return ['node', '/app/plugin/index.js']
        elif execution.runtime_type == 'python':
            return ['python', '/app/plugin/main.py']
        elif execution.runtime_type == 'wasm':
            return ['wasmtime', '/app/plugin/plugin.wasm']
        else:
            raise ValueError(f"Unsupported runtime: {execution.runtime_type}")
    
    async def _monitor_execution(
        self, 
        container: docker.models.containers.Container,
        execution: PluginExecution,
        start_time: float
    ) -> Dict[str, Any]:
        """Monitor container execution with timeout and resource monitoring"""
        timeout = execution.limits.timeout_seconds
        
        # Wait for completion or timeout
        try:
            exit_code = container.wait(timeout=timeout)['StatusCode']
        except Exception:
            # Timeout or other error
            container.kill()
            raise TimeoutError(f"Plugin execution timed out after {timeout}s")
        
        # Get execution logs
        logs = container.logs(stdout=True, stderr=True).decode('utf-8')
        
        # Get resource usage stats (if available)
        stats = None
        try:
            stats = container.stats(stream=False)
        except Exception:
            pass
        
        return {
            'exit_code': exit_code,
            'logs': logs,
            'stats': stats,
            'execution_time': time.time() - start_time
        }


class WasmSandbox:
    """WASM-based sandboxed execution using Wasmtime"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def execute_plugin(self, execution: PluginExecution) -> Dict[str, Any]:
        """Execute WASM plugin"""
        try:
            import wasmtime
            
            # Configure WASM engine with security constraints
            config = wasmtime.Config()
            config.cranelift_opt_level = wasmtime.OptLevel.none
            config.consume_fuel = True
            config.epoch_interruption = True
            
            engine = wasmtime.Engine(config)
            linker = wasmtime.Linker(engine)
            store = wasmtime.Store(engine)
            
            # Set fuel for execution limits
            store.set_fuel(1000000)  # Adjust based on needs
            
            # Load WASM module
            wasm_bytes = Path(execution.code_path).read_bytes()
            module = wasmtime.Module(engine, wasm_bytes)
            
            # Configure WASI with restricted capabilities
            wasi_config = wasmtime.WasiConfig()
            wasi_config.inherit_stdout()
            wasi_config.inherit_stderr()
            
            # Restrict filesystem access
            if execution.limits.filesystem_read:
                for path in execution.limits.filesystem_read:
                    wasi_config.preopen_dir(path, path)
            
            if execution.limits.temp_access:
                temp_dir = tempfile.mkdtemp()
                wasi_config.preopen_dir(temp_dir, '/tmp')
            
            store.set_wasi(wasi_config)
            linker.define_wasi()
            
            # Instantiate and run
            instance = linker.instantiate(store, module)
            start_func = instance.exports(store).get("_start")
            
            start_time = time.time()
            
            if start_func:
                start_func(store)
            
            return {
                'success': True,
                'execution_time': time.time() - start_time,
                'fuel_consumed': store.fuel_consumed()
            }
            
        except Exception as e:
            self.logger.error(f"WASM execution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }


class ProcessSandbox:
    """Process-based sandboxed execution (fallback)"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def execute_plugin(self, execution: PluginExecution) -> Dict[str, Any]:
        """Execute plugin in restricted subprocess"""
        try:
            # Set resource limits
            def set_limits():
                # CPU time limit
                resource.setrlimit(resource.RLIMIT_CPU, (execution.limits.timeout_seconds, execution.limits.timeout_seconds))
                
                # Memory limit (approximate)
                memory_bytes = self._parse_memory(execution.limits.memory_limit)
                resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
                
                # File descriptor limit
                resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
                
                # Process limit
                resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
            
            # Prepare command
            if execution.runtime_type == 'python':
                cmd = [sys.executable, os.path.join(execution.code_path, 'main.py')]
            elif execution.runtime_type == 'typescript':
                cmd = ['node', os.path.join(execution.code_path, 'index.js')]
            else:
                raise ValueError(f"Unsupported runtime: {execution.runtime_type}")
            
            # Set environment
            env = os.environ.copy()
            env.update({
                'PLUGIN_ID': execution.plugin_id,
                'PLUGIN_CONFIG': json.dumps(execution.config),
                'PLUGIN_CONTEXT': json.dumps(execution.context),
                'PLUGIN_MANIFEST': json.dumps(execution.manifest)
            })
            
            # Execute with timeout
            start_time = time.time()
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=execution.code_path,
                preexec_fn=set_limits
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=execution.limits.timeout_seconds
                )
                
                return {
                    'success': process.returncode == 0,
                    'exit_code': process.returncode,
                    'stdout': stdout.decode('utf-8'),
                    'stderr': stderr.decode('utf-8'),
                    'execution_time': time.time() - start_time
                }
                
            except asyncio.TimeoutError:
                process.kill()
                raise TimeoutError(f"Plugin execution timed out after {execution.limits.timeout_seconds}s")
        
        except Exception as e:
            self.logger.error(f"Process execution failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_memory(self, memory_str: str) -> int:
        """Parse memory string to bytes"""
        import re
        match = re.match(r'^(\d+)([KMGT]?)$', memory_str.upper())
        if not match:
            return 256 * 1024 * 1024  # 256MB default
        
        value = int(match.group(1))
        unit = match.group(2)
        
        multipliers = {'': 1, 'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
        return value * multipliers.get(unit, 1)


class PluginExecutor:
    """Main plugin executor with multiple sandbox backends"""
    
    def __init__(self, preferred_backend: str = 'docker'):
        self.logger = logging.getLogger(__name__)
        self.preferred_backend = preferred_backend
        
        # Initialize sandbox backends
        self.backends = {}
        
        try:
            self.backends['docker'] = PluginSandbox()
        except Exception as e:
            self.logger.warning(f"Docker backend not available: {e}")
        
        try:
            self.backends['wasm'] = WasmSandbox()
        except Exception as e:
            self.logger.warning(f"WASM backend not available: {e}")
        
        self.backends['process'] = ProcessSandbox()  # Always available as fallback
    
    async def execute(self, execution: PluginExecution) -> Dict[str, Any]:
        """Execute plugin using best available sandbox"""
        
        # Choose backend based on runtime and availability
        backend_name = self._choose_backend(execution)
        backend = self.backends.get(backend_name)
        
        if not backend:
            return {
                'success': False,
                'error': f'No suitable execution backend available'
            }
        
        self.logger.info(f"Executing plugin {execution.plugin_id} using {backend_name} backend")
        
        try:
            result = await backend.execute_plugin(execution)
            result['backend'] = backend_name
            return result
        
        except Exception as e:
            self.logger.error(f"Execution failed with {backend_name}: {e}")
            
            # Try fallback to process sandbox
            if backend_name != 'process' and 'process' in self.backends:
                self.logger.info("Falling back to process sandbox")
                try:
                    result = await self.backends['process'].execute_plugin(execution)
                    result['backend'] = 'process'
                    return result
                except Exception as fallback_error:
                    return {
                        'success': False,
                        'error': f'All backends failed: {e}, {fallback_error}'
                    }
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _choose_backend(self, execution: PluginExecution) -> str:
        """Choose best sandbox backend for execution"""
        runtime = execution.runtime_type
        
        # WASM runtime should use WASM backend
        if runtime == 'wasm' and 'wasm' in self.backends:
            return 'wasm'
        
        # Prefer Docker for better isolation
        if 'docker' in self.backends:
            return 'docker'
        
        # Fallback to process sandbox
        return 'process'


async def main():
    """Main entry point for standalone execution"""
    if len(sys.argv) < 2:
        print("Usage: plugin-executor.py <execution_config.json>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    with open(config_path) as f:
        config = json.load(f)
    
    # Create execution configuration
    execution = PluginExecution(
        plugin_id=config['plugin_id'],
        runtime_type=config['runtime_type'],
        code_path=config['code_path'],
        manifest=config['manifest'],
        config=config.get('config', {}),
        limits=ResourceLimits(**config.get('limits', {})),
        context=config.get('context', {})
    )
    
    # Execute plugin
    executor = PluginExecutor()
    result = await executor.execute(execution)
    
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    asyncio.run(main())