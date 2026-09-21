#!/usr/bin/env python3
"""
Chaos Engineering Testing Engine for ActiveLog E2E Testing Suite.

This module provides comprehensive chaos engineering testing including
infrastructure failures, network partitions, resource exhaustion,
dependency failures, and system resilience validation.
"""

import asyncio
import json
import time
import random
import subprocess
import signal
import psutil
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from enum import Enum
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests
import socket
import os

class ChaosExperimentType(Enum):
    CPU_STRESS = "cpu_stress"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    DISK_SPACE_FILL = "disk_space_fill"
    NETWORK_PARTITION = "network_partition"
    NETWORK_LATENCY = "network_latency"
    NETWORK_PACKET_LOSS = "network_packet_loss"
    SERVICE_KILL = "service_kill"
    DEPENDENCY_FAILURE = "dependency_failure"
    DATABASE_SLOWDOWN = "database_slowdown"
    FILE_CORRUPTION = "file_corruption"
    TIME_SKEW = "time_skew"
    RANDOM_SHUTDOWN = "random_shutdown"

class ChaosImpact(Enum):
    MINIMAL = "minimal"
    MODERATE = "moderate"  
    SEVERE = "severe"
    CRITICAL = "critical"

class SystemComponent(Enum):
    WEB_SERVER = "web_server"
    DATABASE = "database"
    CACHE = "cache"
    LOAD_BALANCER = "load_balancer"
    MESSAGE_QUEUE = "message_queue"
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    ENTIRE_SYSTEM = "entire_system"

class RecoveryStatus(Enum):
    RECOVERED = "recovered"
    DEGRADED = "degraded" 
    FAILED = "failed"
    UNKNOWN = "unknown"

@dataclass
class ChaosExperiment:
    id: str
    name: str
    experiment_type: ChaosExperimentType
    target_component: SystemComponent
    duration_seconds: int
    expected_impact: ChaosImpact
    blast_radius: str  # Description of affected components
    hypothesis: str  # What we expect to happen
    rollback_strategy: str
    steady_state_definition: Dict[str, Any]
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_connections: int
    response_time_ms: float
    error_rate_percent: float
    throughput_rps: float

@dataclass
class ChaosExperimentResult:
    experiment_id: str
    experiment_name: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    actual_impact: Optional[ChaosImpact] = None
    hypothesis_confirmed: bool = False
    recovery_status: RecoveryStatus = RecoveryStatus.UNKNOWN
    recovery_time_seconds: Optional[float] = None
    baseline_metrics: Optional[SystemMetrics] = None
    during_chaos_metrics: List[SystemMetrics] = field(default_factory=list)
    post_chaos_metrics: Optional[SystemMetrics] = None
    lessons_learned: List[str] = field(default_factory=list)
    issues_discovered: List[str] = field(default_factory=list)
    error_logs: List[str] = field(default_factory=list)

class SystemMonitor:
    def __init__(self, target_url: str = "http://localhost:8080"):
        self.target_url = target_url
        self.monitoring = False
        self.metrics_history = []
        self.session = requests.Session()

    def start_monitoring(self, interval_seconds: float = 1.0):
        self.monitoring = True
        threading.Thread(target=self._monitoring_loop, args=(interval_seconds,), daemon=True).start()

    def stop_monitoring(self):
        self.monitoring = False

    def _monitoring_loop(self, interval_seconds: float):
        while self.monitoring:
            try:
                metrics = self._collect_metrics()
                self.metrics_history.append(metrics)
                
                if len(self.metrics_history) > 1000:  # Limit history size
                    self.metrics_history = self.metrics_history[-500:]
                    
            except Exception as e:
                logging.error(f"Metrics collection failed: {e}")
            
            time.sleep(interval_seconds)

    def _collect_metrics(self) -> SystemMetrics:
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        try:
            start_time = time.time()
            response = self.session.get(f"{self.target_url}/health", timeout=5)
            response_time = (time.time() - start_time) * 1000
            error_rate = 0.0 if response.status_code == 200 else 100.0
        except Exception:
            response_time = 5000.0  # Timeout
            error_rate = 100.0
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_usage_percent=cpu_usage,
            memory_usage_percent=memory.percent,
            disk_usage_percent=disk.percent,
            network_bytes_sent=network.bytes_sent,
            network_bytes_recv=network.bytes_recv,
            active_connections=len(psutil.net_connections()),
            response_time_ms=response_time,
            error_rate_percent=error_rate,
            throughput_rps=1000.0 / max(response_time, 1)  # Rough estimate
        )

    def get_current_metrics(self) -> SystemMetrics:
        return self._collect_metrics()

    def get_metrics_during_period(self, start_time: datetime, end_time: datetime) -> List[SystemMetrics]:
        return [
            m for m in self.metrics_history 
            if start_time <= m.timestamp <= end_time
        ]

class CPUStressChaos:
    def __init__(self):
        self.stress_processes = []

    async def start_chaos(self, parameters: Dict[str, Any]) -> bool:
        try:
            cpu_cores = parameters.get('cpu_cores', psutil.cpu_count())
            duration = parameters.get('duration_seconds', 60)
            
            for i in range(cpu_cores):
                process = subprocess.Popen([
                    'python3', '-c',
                    'import time; [x*x for x in range(10000000) for _ in range(1000)]'
                ])
                self.stress_processes.append(process)
            
            await asyncio.sleep(duration)
            return True
            
        except Exception as e:
            logging.error(f"CPU stress chaos failed: {e}")
            return False

    async def stop_chaos(self):
        for process in self.stress_processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception as e:
                logging.error(f"Failed to terminate CPU stress process: {e}")
                try:
                    process.kill()
                except:
                    pass
        
        self.stress_processes.clear()

class MemoryExhaustionChaos:
    def __init__(self):
        self.memory_hogs = []

    async def start_chaos(self, parameters: Dict[str, Any]) -> bool:
        try:
            memory_mb = parameters.get('memory_mb', 1024)
            duration = parameters.get('duration_seconds', 60)
            
            def consume_memory():
                chunk_size = 100 * 1024 * 1024  # 100MB chunks
                chunks = []
                try:
                    for _ in range(memory_mb // 100):
                        chunk = bytearray(chunk_size)
                        chunks.append(chunk)
                        time.sleep(0.1)
                    
                    time.sleep(duration)
                except MemoryError:
                    pass
                finally:
                    chunks.clear()
            
            thread = threading.Thread(target=consume_memory, daemon=True)
            thread.start()
            self.memory_hogs.append(thread)
            
            return True
            
        except Exception as e:
            logging.error(f"Memory exhaustion chaos failed: {e}")
            return False

    async def stop_chaos(self):
        # Memory will be released when threads finish
        pass

class NetworkLatencyChaos:
    def __init__(self):
        self.tc_rules_applied = False

    async def start_chaos(self, parameters: Dict[str, Any]) -> bool:
        try:
            interface = parameters.get('interface', 'lo')
            latency_ms = parameters.get('latency_ms', 100)
            
            # Use tc (traffic control) to add latency
            cmd = [
                'sudo', 'tc', 'qdisc', 'add', 'dev', interface,
                'root', 'netem', 'delay', f'{latency_ms}ms'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.tc_rules_applied = True
                return True
            else:
                logging.error(f"Failed to apply network latency: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"Network latency chaos failed: {e}")
            return False

    async def stop_chaos(self):
        if self.tc_rules_applied:
            try:
                cmd = ['sudo', 'tc', 'qdisc', 'del', 'dev', 'lo', 'root']
                subprocess.run(cmd, capture_output=True)
                self.tc_rules_applied = False
            except Exception as e:
                logging.error(f"Failed to remove network latency rules: {e}")

class ServiceKillChaos:
    def __init__(self):
        self.killed_processes = []

    async def start_chaos(self, parameters: Dict[str, Any]) -> bool:
        try:
            service_name = parameters.get('service_name', 'python3')
            kill_signal = parameters.get('signal', 'SIGTERM')
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if service_name.lower() in proc.info['name'].lower():
                        if 'chaos_engineering_engine.py' not in ' '.join(proc.info['cmdline']):
                            self.killed_processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name']
                            })
                            
                            if kill_signal == 'SIGTERM':
                                proc.terminate()
                            elif kill_signal == 'SIGKILL':
                                proc.kill()
                            
                            logging.info(f"Killed process {proc.info['name']} (PID: {proc.info['pid']})")
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return len(self.killed_processes) > 0
            
        except Exception as e:
            logging.error(f"Service kill chaos failed: {e}")
            return False

    async def stop_chaos(self):
        # Services should auto-restart or be manually restarted
        logging.info(f"Killed {len(self.killed_processes)} processes during chaos experiment")

class DiskSpaceFillChaos:
    def __init__(self):
        self.temp_files = []

    async def start_chaos(self, parameters: Dict[str, Any]) -> bool:
        try:
            fill_size_mb = parameters.get('fill_size_mb', 1024)
            temp_dir = parameters.get('temp_dir', '/tmp')
            
            chunk_size = 100 * 1024 * 1024  # 100MB chunks
            num_chunks = fill_size_mb // 100
            
            for i in range(num_chunks):
                temp_file = f"{temp_dir}/chaos_fill_{i}.tmp"
                
                with open(temp_file, 'wb') as f:
                    f.write(os.urandom(chunk_size))
                
                self.temp_files.append(temp_file)
                
                if i % 5 == 0:  # Check disk space every 5 files
                    disk_usage = psutil.disk_usage(temp_dir)
                    if disk_usage.percent > 95:  # Stop if disk > 95% full
                        break
            
            return True
            
        except Exception as e:
            logging.error(f"Disk space fill chaos failed: {e}")
            return False

    async def stop_chaos(self):
        for temp_file in self.temp_files:
            try:
                os.remove(temp_file)
            except Exception as e:
                logging.error(f"Failed to remove temp file {temp_file}: {e}")
        
        self.temp_files.clear()

class ChaosEngineeringEngine:
    def __init__(self, target_url: str = "http://localhost:8080", results_dir: str = "chaos_results"):
        self.target_url = target_url
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.monitor = SystemMonitor(target_url)
        self.experiments = self._create_chaos_experiments()
        
        self.chaos_implementations = {
            ChaosExperimentType.CPU_STRESS: CPUStressChaos(),
            ChaosExperimentType.MEMORY_EXHAUSTION: MemoryExhaustionChaos(),
            ChaosExperimentType.NETWORK_LATENCY: NetworkLatencyChaos(),
            ChaosExperimentType.SERVICE_KILL: ServiceKillChaos(),
            ChaosExperimentType.DISK_SPACE_FILL: DiskSpaceFillChaos()
        }

    def _create_chaos_experiments(self) -> List[ChaosExperiment]:
        return [
            ChaosExperiment(
                id="cpu_stress_moderate",
                name="Moderate CPU Stress Test",
                experiment_type=ChaosExperimentType.CPU_STRESS,
                target_component=SystemComponent.WEB_SERVER,
                duration_seconds=60,
                expected_impact=ChaosImpact.MODERATE,
                blast_radius="Single server CPU resources",
                hypothesis="System should maintain >80% availability during moderate CPU stress",
                rollback_strategy="Kill stress processes",
                steady_state_definition={"response_time_ms": "<500", "error_rate": "<5%"},
                parameters={"cpu_cores": 2, "duration_seconds": 60}
            ),
            ChaosExperiment(
                id="memory_exhaustion",
                name="Memory Exhaustion Test",
                experiment_type=ChaosExperimentType.MEMORY_EXHAUSTION,
                target_component=SystemComponent.WEB_SERVER,
                duration_seconds=45,
                expected_impact=ChaosImpact.SEVERE,
                blast_radius="Application memory space",
                hypothesis="System should gracefully handle memory pressure with minimal service degradation",
                rollback_strategy="Release memory allocations",
                steady_state_definition={"response_time_ms": "<1000", "error_rate": "<10%"},
                parameters={"memory_mb": 2048, "duration_seconds": 45}
            ),
            ChaosExperiment(
                id="network_latency_high",
                name="High Network Latency Test",
                experiment_type=ChaosExperimentType.NETWORK_LATENCY,
                target_component=SystemComponent.NETWORK,
                duration_seconds=90,
                expected_impact=ChaosImpact.MODERATE,
                blast_radius="All network communications",
                hypothesis="System should maintain functionality with increased response times",
                rollback_strategy="Remove traffic control rules",
                steady_state_definition={"response_time_ms": "<2000", "error_rate": "<5%"},
                parameters={"interface": "lo", "latency_ms": 200, "duration_seconds": 90}
            ),
            ChaosExperiment(
                id="service_process_kill",
                name="Random Service Process Kill",
                experiment_type=ChaosExperimentType.SERVICE_KILL,
                target_component=SystemComponent.WEB_SERVER,
                duration_seconds=30,
                expected_impact=ChaosImpact.SEVERE,
                blast_radius="Target service processes",
                hypothesis="System should auto-recover or restart killed processes within 30 seconds",
                rollback_strategy="Manual service restart if needed",
                steady_state_definition={"availability": ">90%", "recovery_time": "<30s"},
                parameters={"service_name": "python3", "signal": "SIGTERM"}
            ),
            ChaosExperiment(
                id="disk_space_fill",
                name="Disk Space Exhaustion Test",
                experiment_type=ChaosExperimentType.DISK_SPACE_FILL,
                target_component=SystemComponent.FILE_SYSTEM,
                duration_seconds=120,
                expected_impact=ChaosImpact.CRITICAL,
                blast_radius="File system operations",
                hypothesis="System should handle disk space exhaustion gracefully with proper error handling",
                rollback_strategy="Remove temporary files",
                steady_state_definition={"disk_usage": "<90%", "write_operations": "functional"},
                parameters={"fill_size_mb": 1024, "temp_dir": "/tmp"}
            )
        ]

    async def run_chaos_experiment(self, experiment: ChaosExperiment) -> ChaosExperimentResult:
        result = ChaosExperimentResult(
            experiment_id=experiment.id,
            experiment_name=experiment.name,
            status="running",
            start_time=datetime.now()
        )
        
        try:
            print(f"Starting chaos experiment: {experiment.name}")
            
            # Collect baseline metrics
            self.monitor.start_monitoring(interval_seconds=1.0)
            await asyncio.sleep(10)  # 10 seconds baseline
            result.baseline_metrics = self.monitor.get_current_metrics()
            
            # Start chaos
            chaos_impl = self.chaos_implementations.get(experiment.experiment_type)
            if not chaos_impl:
                raise ValueError(f"No implementation for {experiment.experiment_type}")
            
            chaos_start = datetime.now()
            chaos_started = await chaos_impl.start_chaos(experiment.parameters)
            
            if not chaos_started:
                result.status = "failed"
                result.issues_discovered.append("Failed to start chaos experiment")
                return result
            
            # Monitor during chaos
            print(f"Chaos active for {experiment.duration_seconds} seconds...")
            await asyncio.sleep(experiment.duration_seconds)
            
            # Stop chaos
            await chaos_impl.stop_chaos()
            chaos_end = datetime.now()
            
            # Collect metrics during chaos period
            result.during_chaos_metrics = self.monitor.get_metrics_during_period(
                chaos_start, chaos_end
            )
            
            # Monitor recovery
            print("Monitoring recovery...")
            recovery_start = time.time()
            recovery_detected = False
            
            for _ in range(60):  # Monitor for up to 60 seconds
                current_metrics = self.monitor.get_current_metrics()
                
                if self._is_system_recovered(current_metrics, result.baseline_metrics, experiment):
                    recovery_detected = True
                    result.recovery_time_seconds = time.time() - recovery_start
                    result.recovery_status = RecoveryStatus.RECOVERED
                    break
                
                await asyncio.sleep(1)
            
            if not recovery_detected:
                result.recovery_status = RecoveryStatus.DEGRADED
                result.issues_discovered.append("System did not fully recover within 60 seconds")
            
            # Final metrics
            result.post_chaos_metrics = self.monitor.get_current_metrics()
            
            # Analyze results
            result.actual_impact = self._assess_actual_impact(result)
            result.hypothesis_confirmed = self._validate_hypothesis(experiment, result)
            result.lessons_learned = self._extract_lessons_learned(experiment, result)
            
            result.status = "completed"
            
        except Exception as e:
            result.status = "error"
            result.issues_discovered.append(f"Experiment execution error: {str(e)}")
            logging.error(f"Chaos experiment {experiment.id} failed: {e}")
        
        finally:
            result.end_time = datetime.now()
            self.monitor.stop_monitoring()
            
            # Ensure cleanup
            try:
                chaos_impl = self.chaos_implementations.get(experiment.experiment_type)
                if chaos_impl:
                    await chaos_impl.stop_chaos()
            except Exception as e:
                logging.error(f"Cleanup failed for {experiment.id}: {e}")
        
        return result

    def _is_system_recovered(self, current: SystemMetrics, baseline: SystemMetrics, experiment: ChaosExperiment) -> bool:
        # Define recovery criteria based on experiment type
        if experiment.experiment_type == ChaosExperimentType.CPU_STRESS:
            return (current.cpu_usage_percent <= baseline.cpu_usage_percent * 1.2 and
                    current.response_time_ms <= baseline.response_time_ms * 1.5)
        
        elif experiment.experiment_type == ChaosExperimentType.MEMORY_EXHAUSTION:
            return (current.memory_usage_percent <= baseline.memory_usage_percent * 1.1 and
                    current.response_time_ms <= baseline.response_time_ms * 2.0)
        
        elif experiment.experiment_type == ChaosExperimentType.NETWORK_LATENCY:
            return current.response_time_ms <= baseline.response_time_ms * 1.3
        
        elif experiment.experiment_type == ChaosExperimentType.SERVICE_KILL:
            return current.error_rate_percent <= 5.0
        
        elif experiment.experiment_type == ChaosExperimentType.DISK_SPACE_FILL:
            return current.disk_usage_percent <= baseline.disk_usage_percent * 1.1
        
        # Default recovery criteria
        return (current.response_time_ms <= baseline.response_time_ms * 2.0 and
                current.error_rate_percent <= 10.0)

    def _assess_actual_impact(self, result: ChaosExperimentResult) -> ChaosImpact:
        if not result.baseline_metrics or not result.during_chaos_metrics:
            return ChaosImpact.UNKNOWN
        
        baseline = result.baseline_metrics
        avg_chaos_metrics = self._average_metrics(result.during_chaos_metrics)
        
        response_time_increase = (avg_chaos_metrics.response_time_ms - baseline.response_time_ms) / baseline.response_time_ms
        error_rate = avg_chaos_metrics.error_rate_percent
        
        if error_rate > 50 or response_time_increase > 10:
            return ChaosImpact.CRITICAL
        elif error_rate > 20 or response_time_increase > 5:
            return ChaosImpact.SEVERE
        elif error_rate > 5 or response_time_increase > 2:
            return ChaosImpact.MODERATE
        else:
            return ChaosImpact.MINIMAL

    def _average_metrics(self, metrics_list: List[SystemMetrics]) -> SystemMetrics:
        if not metrics_list:
            return SystemMetrics(datetime.now(), 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        count = len(metrics_list)
        return SystemMetrics(
            timestamp=metrics_list[0].timestamp,
            cpu_usage_percent=sum(m.cpu_usage_percent for m in metrics_list) / count,
            memory_usage_percent=sum(m.memory_usage_percent for m in metrics_list) / count,
            disk_usage_percent=sum(m.disk_usage_percent for m in metrics_list) / count,
            network_bytes_sent=sum(m.network_bytes_sent for m in metrics_list) // count,
            network_bytes_recv=sum(m.network_bytes_recv for m in metrics_list) // count,
            active_connections=sum(m.active_connections for m in metrics_list) // count,
            response_time_ms=sum(m.response_time_ms for m in metrics_list) / count,
            error_rate_percent=sum(m.error_rate_percent for m in metrics_list) / count,
            throughput_rps=sum(m.throughput_rps for m in metrics_list) / count
        )

    def _validate_hypothesis(self, experiment: ChaosExperiment, result: ChaosExperimentResult) -> bool:
        # Parse steady state definition and check if maintained
        steady_state = experiment.steady_state_definition
        
        if not result.during_chaos_metrics:
            return False
        
        avg_metrics = self._average_metrics(result.during_chaos_metrics)
        
        for criterion, threshold in steady_state.items():
            if criterion == "response_time_ms" and threshold.startswith("<"):
                max_allowed = float(threshold[1:])
                if avg_metrics.response_time_ms >= max_allowed:
                    return False
            
            elif criterion == "error_rate" and threshold.endswith("%"):
                max_allowed = float(threshold[:-1])
                if avg_metrics.error_rate_percent >= max_allowed:
                    return False
            
            elif criterion == "availability" and threshold.startswith(">"):
                min_required = float(threshold[1:-1])  # Remove > and %
                availability = 100 - avg_metrics.error_rate_percent
                if availability <= min_required:
                    return False
        
        return True

    def _extract_lessons_learned(self, experiment: ChaosExperiment, result: ChaosExperimentResult) -> List[str]:
        lessons = []
        
        if result.status == "completed":
            if result.hypothesis_confirmed:
                lessons.append(f"System met resilience expectations for {experiment.experiment_type.value}")
            else:
                lessons.append(f"System did not meet resilience expectations - need improvements")
            
            if result.recovery_status == RecoveryStatus.RECOVERED:
                if result.recovery_time_seconds and result.recovery_time_seconds < 30:
                    lessons.append("System showed excellent recovery capabilities")
                else:
                    lessons.append("System recovery was slower than optimal")
            
            if result.actual_impact != experiment.expected_impact:
                lessons.append(f"Actual impact ({result.actual_impact.value}) differed from expected ({experiment.expected_impact.value})")
        
        if result.issues_discovered:
            lessons.append("Issues discovered that need attention")
        
        return lessons

    async def run_chaos_test_suite(self, experiment_ids: List[str] = None) -> Dict[str, Any]:
        experiments_to_run = self.experiments
        if experiment_ids:
            experiments_to_run = [e for e in self.experiments if e.id in experiment_ids]
        
        print("Starting comprehensive chaos engineering test suite...")
        results = []
        
        for experiment in experiments_to_run:
            print(f"\n{'='*60}")
            print(f"Experiment: {experiment.name}")
            print(f"Expected Impact: {experiment.expected_impact.value}")
            print(f"Hypothesis: {experiment.hypothesis}")
            
            result = await self.run_chaos_experiment(experiment)
            results.append(result)
            
            print(f"Status: {result.status}")
            print(f"Actual Impact: {result.actual_impact.value if result.actual_impact else 'Unknown'}")
            print(f"Hypothesis Confirmed: {result.hypothesis_confirmed}")
            print(f"Recovery Status: {result.recovery_status.value}")
            
            # Wait between experiments to allow system stabilization
            print("Waiting 30 seconds before next experiment...")
            await asyncio.sleep(30)
        
        summary = self._generate_test_summary(results)
        return {
            "results": results,
            "summary": summary
        }

    def _generate_test_summary(self, results: List[ChaosExperimentResult]) -> Dict[str, Any]:
        total_experiments = len(results)
        completed_experiments = len([r for r in results if r.status == "completed"])
        successful_recoveries = len([r for r in results if r.recovery_status == RecoveryStatus.RECOVERED])
        confirmed_hypotheses = len([r for r in results if r.hypothesis_confirmed])
        
        total_issues = sum(len(r.issues_discovered) for r in results)
        total_lessons = sum(len(r.lessons_learned) for r in results)
        
        impact_distribution = {}
        for result in results:
            if result.actual_impact:
                impact = result.actual_impact.value
                impact_distribution[impact] = impact_distribution.get(impact, 0) + 1
        
        avg_recovery_time = None
        recovery_times = [r.recovery_time_seconds for r in results if r.recovery_time_seconds]
        if recovery_times:
            avg_recovery_time = sum(recovery_times) / len(recovery_times)
        
        return {
            "total_experiments": total_experiments,
            "completed_experiments": completed_experiments,
            "success_rate": (completed_experiments / total_experiments) * 100 if total_experiments > 0 else 0,
            "successful_recoveries": successful_recoveries,
            "recovery_rate": (successful_recoveries / total_experiments) * 100 if total_experiments > 0 else 0,
            "confirmed_hypotheses": confirmed_hypotheses,
            "hypothesis_accuracy": (confirmed_hypotheses / total_experiments) * 100 if total_experiments > 0 else 0,
            "total_issues_discovered": total_issues,
            "total_lessons_learned": total_lessons,
            "impact_distribution": impact_distribution,
            "average_recovery_time_seconds": avg_recovery_time,
            "resilience_score": self._calculate_resilience_score(results)
        }

    def _calculate_resilience_score(self, results: List[ChaosExperimentResult]) -> float:
        if not results:
            return 0.0
        
        scores = []
        for result in results:
            experiment_score = 0.0
            
            # Base score for completion
            if result.status == "completed":
                experiment_score += 25
            
            # Recovery capability
            if result.recovery_status == RecoveryStatus.RECOVERED:
                experiment_score += 25
                if result.recovery_time_seconds and result.recovery_time_seconds < 30:
                    experiment_score += 10  # Fast recovery bonus
            
            # Hypothesis validation
            if result.hypothesis_confirmed:
                experiment_score += 20
            
            # Impact assessment
            if result.actual_impact:
                if result.actual_impact == ChaosImpact.MINIMAL:
                    experiment_score += 20
                elif result.actual_impact == ChaosImpact.MODERATE:
                    experiment_score += 15
                elif result.actual_impact == ChaosImpact.SEVERE:
                    experiment_score += 10
                # Critical impact gets 0 additional points
            
            scores.append(min(experiment_score, 100))  # Cap at 100
        
        return sum(scores) / len(scores)

    def generate_chaos_report(self, test_results: Dict[str, Any], output_path: str):
        results = test_results["results"]
        summary = test_results["summary"]
        
        report = {
            "chaos_test_summary": {
                "total_experiments": summary["total_experiments"],
                "completed_experiments": summary["completed_experiments"],
                "success_rate": summary["success_rate"],
                "successful_recoveries": summary["successful_recoveries"],
                "recovery_rate": summary["recovery_rate"],
                "confirmed_hypotheses": summary["confirmed_hypotheses"],
                "hypothesis_accuracy": summary["hypothesis_accuracy"],
                "resilience_score": summary["resilience_score"],
                "timestamp": datetime.now().isoformat()
            },
            "system_resilience": {
                "total_issues_discovered": summary["total_issues_discovered"],
                "total_lessons_learned": summary["total_lessons_learned"],
                "impact_distribution": summary["impact_distribution"],
                "average_recovery_time_seconds": summary["average_recovery_time_seconds"]
            },
            "detailed_results": []
        }
        
        for result in results:
            experiment_data = {
                "experiment_id": result.experiment_id,
                "experiment_name": result.experiment_name,
                "status": result.status,
                "start_time": result.start_time.isoformat(),
                "end_time": result.end_time.isoformat() if result.end_time else None,
                "execution_duration": (result.end_time - result.start_time).total_seconds() if result.end_time else None,
                "actual_impact": result.actual_impact.value if result.actual_impact else None,
                "hypothesis_confirmed": result.hypothesis_confirmed,
                "recovery_status": result.recovery_status.value,
                "recovery_time_seconds": result.recovery_time_seconds,
                "issues_discovered": result.issues_discovered,
                "lessons_learned": result.lessons_learned,
                "baseline_metrics": {
                    "cpu_usage": result.baseline_metrics.cpu_usage_percent if result.baseline_metrics else None,
                    "memory_usage": result.baseline_metrics.memory_usage_percent if result.baseline_metrics else None,
                    "response_time_ms": result.baseline_metrics.response_time_ms if result.baseline_metrics else None,
                    "error_rate": result.baseline_metrics.error_rate_percent if result.baseline_metrics else None
                },
                "chaos_impact_metrics": {
                    "max_response_time_ms": max((m.response_time_ms for m in result.during_chaos_metrics), default=0),
                    "max_error_rate": max((m.error_rate_percent for m in result.during_chaos_metrics), default=0),
                    "avg_cpu_usage": sum(m.cpu_usage_percent for m in result.during_chaos_metrics) / len(result.during_chaos_metrics) if result.during_chaos_metrics else 0,
                    "avg_memory_usage": sum(m.memory_usage_percent for m in result.during_chaos_metrics) / len(result.during_chaos_metrics) if result.during_chaos_metrics else 0
                }
            }
            
            report["detailed_results"].append(experiment_data)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        html_report_path = output_path.replace('.json', '.html')
        self.generate_html_report(report, html_report_path)

    def generate_html_report(self, report_data: Dict[str, Any], output_path: str):
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Chaos Engineering Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; padding: 20px; background: #dc3545; color: white; border-radius: 6px; }}
                .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .summary-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }}
                .summary-card h3 {{ margin: 0; color: #333; }}
                .summary-card .value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .resilience-score {{ font-size: 3em; font-weight: bold; }}
                .score-excellent {{ color: #28a745; }}
                .score-good {{ color: #ffc107; }}
                .score-poor {{ color: #dc3545; }}
                .resilience-section {{ background: #e8f5e8; padding: 20px; border-radius: 6px; margin-bottom: 30px; }}
                .experiment-results {{ margin-bottom: 30px; }}
                .experiment-item {{ background: #f8f9fa; padding: 20px; margin-bottom: 15px; border-radius: 4px; border-left: 4px solid #28a745; }}
                .experiment-item.failed {{ border-left-color: #dc3545; }}
                .experiment-item.degraded {{ border-left-color: #ffc107; }}
                .experiment-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }}
                .experiment-details {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
                .detail-section {{ background: white; padding: 15px; border-radius: 4px; }}
                .metrics-comparison {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
                .metric-card {{ background: #f8f9fa; padding: 10px; border-radius: 4px; text-align: center; }}
                .impact-badge {{ padding: 4px 12px; border-radius: 12px; color: white; font-weight: bold; }}
                .impact-minimal {{ background: #28a745; }}
                .impact-moderate {{ background: #ffc107; color: #212529; }}
                .impact-severe {{ background: #fd7e14; }}
                .impact-critical {{ background: #dc3545; }}
                .status-badge {{ padding: 4px 8px; border-radius: 12px; color: white; font-weight: bold; }}
                .status-completed {{ background: #28a745; }}
                .status-failed {{ background: #dc3545; }}
                .status-error {{ background: #6c757d; }}
                .recovery-badge {{ padding: 4px 8px; border-radius: 12px; color: white; font-weight: bold; }}
                .recovery-recovered {{ background: #28a745; }}
                .recovery-degraded {{ background: #ffc107; color: #212529; }}
                .recovery-failed {{ background: #dc3545; }}
                .issues-list {{ background: #f8d7da; padding: 15px; border-radius: 4px; margin-top: 10px; }}
                .lessons-list {{ background: #d1ecf1; padding: 15px; border-radius: 4px; margin-top: 10px; }}
                .hypothesis-result {{ font-weight: bold; }}
                .hypothesis-confirmed {{ color: #28a745; }}
                .hypothesis-rejected {{ color: #dc3545; }}
                .chart {{ margin: 15px 0; }}
                .bar {{ height: 25px; background: #e9ecef; border-radius: 12px; overflow: hidden; margin: 8px 0; }}
                .bar-fill {{ height: 100%; display: flex; align-items: center; padding: 0 12px; color: white; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💥 Chaos Engineering Test Report</h1>
                    <p>System Resilience & Fault Tolerance Analysis</p>
                    <p>Generated on {report_data['chaos_test_summary']['timestamp']}</p>
                </div>
                
                <div class="summary">
                    <div class="summary-card">
                        <h3>Total Experiments</h3>
                        <div class="value">{report_data['chaos_test_summary']['total_experiments']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Success Rate</h3>
                        <div class="value {'score-excellent' if report_data['chaos_test_summary']['success_rate'] >= 80 else 'score-good' if report_data['chaos_test_summary']['success_rate'] >= 60 else 'score-poor'}">{report_data['chaos_test_summary']['success_rate']:.1f}%</div>
                    </div>
                    <div class="summary-card">
                        <h3>Recovery Rate</h3>
                        <div class="value {'score-excellent' if report_data['chaos_test_summary']['recovery_rate'] >= 80 else 'score-good' if report_data['chaos_test_summary']['recovery_rate'] >= 60 else 'score-poor'}">{report_data['chaos_test_summary']['recovery_rate']:.1f}%</div>
                    </div>
                    <div class="summary-card">
                        <h3>Hypothesis Accuracy</h3>
                        <div class="value">{report_data['chaos_test_summary']['hypothesis_accuracy']:.1f}%</div>
                    </div>
                    <div class="summary-card">
                        <h3>Resilience Score</h3>
                        <div class="resilience-score {'score-excellent' if report_data['chaos_test_summary']['resilience_score'] >= 80 else 'score-good' if report_data['chaos_test_summary']['resilience_score'] >= 60 else 'score-poor'}">{report_data['chaos_test_summary']['resilience_score']:.1f}</div>
                    </div>
                </div>
                
                <div class="resilience-section">
                    <h3>🛡️ System Resilience Analysis</h3>
                    <div class="metrics-comparison">
                        <div class="metric-card">
                            <h4>Issues Discovered</h4>
                            <div class="value" style="color: #dc3545;">{report_data['system_resilience']['total_issues_discovered']}</div>
                        </div>
                        <div class="metric-card">
                            <h4>Lessons Learned</h4>
                            <div class="value" style="color: #007bff;">{report_data['system_resilience']['total_lessons_learned']}</div>
                        </div>
                        <div class="metric-card">
                            <h4>Avg Recovery Time</h4>
                            <div class="value">{report_data['system_resilience']['average_recovery_time_seconds']:.1f}s</div>
                        </div>
                    </div>
                    
                    <div class="chart">
                        <h4>Impact Distribution</h4>
        """
        
        total_impacts = sum(report_data['system_resilience']['impact_distribution'].values()) or 1
        for impact, count in report_data['system_resilience']['impact_distribution'].items():
            percentage = (count / total_impacts) * 100
            html_content += f"""
                        <div class="bar">
                            <div class="bar-fill impact-{impact}" style="width: {percentage}%;">
                                {impact.upper()}: {count} experiments
                            </div>
                        </div>
            """
        
        html_content += """
                    </div>
                </div>
                
                <div class="experiment-results">
                    <h3>🧪 Detailed Experiment Results</h3>
        """
        
        for exp in report_data['detailed_results']:
            status_class = exp['status'] if exp['recovery_status'] == 'recovered' else exp['recovery_status']
            
            html_content += f"""
                    <div class="experiment-item {status_class}">
                        <div class="experiment-header">
                            <h4>{exp['experiment_name']}</h4>
                            <div>
                                <span class="status-badge status-{exp['status']}">{exp['status'].upper()}</span>
                                <span class="recovery-badge recovery-{exp['recovery_status']}">{exp['recovery_status'].upper()}</span>
                                {f'<span class="impact-badge impact-{exp["actual_impact"]}">{exp["actual_impact"].upper()}</span>' if exp['actual_impact'] else ''}
                            </div>
                        </div>
                        
                        <div class="experiment-details">
                            <div class="detail-section">
                                <h5>📊 Experiment Overview</h5>
                                <p><strong>Duration:</strong> {exp['execution_duration']:.1f}s</p>
                                <p><strong>Recovery Time:</strong> {f"{exp['recovery_time_seconds']:.1f}s" if exp['recovery_time_seconds'] else 'N/A'}</p>
                                <p class="hypothesis-result"><strong>Hypothesis:</strong> 
                                    <span class="{'hypothesis-confirmed' if exp['hypothesis_confirmed'] else 'hypothesis-rejected'}">
                                        {'✅ CONFIRMED' if exp['hypothesis_confirmed'] else '❌ REJECTED'}
                                    </span>
                                </p>
                            </div>
                            
                            <div class="detail-section">
                                <h5>📈 Performance Impact</h5>
                                <div class="metrics-comparison">
                                    <div class="metric-card">
                                        <strong>Baseline Response</strong><br>
                                        {exp['baseline_metrics']['response_time_ms']:.1f}ms
                                    </div>
                                    <div class="metric-card">
                                        <strong>Max During Chaos</strong><br>
                                        {exp['chaos_impact_metrics']['max_response_time_ms']:.1f}ms
                                    </div>
                                </div>
                                <div class="metrics-comparison">
                                    <div class="metric-card">
                                        <strong>Baseline Error Rate</strong><br>
                                        {exp['baseline_metrics']['error_rate']:.1f}%
                                    </div>
                                    <div class="metric-card">
                                        <strong>Max Error Rate</strong><br>
                                        {exp['chaos_impact_metrics']['max_error_rate']:.1f}%
                                    </div>
                                </div>
                            </div>
                            
                            <div class="detail-section">
                                <h5>💻 Resource Utilization</h5>
                                <div class="metrics-comparison">
                                    <div class="metric-card">
                                        <strong>Avg CPU Usage</strong><br>
                                        {exp['chaos_impact_metrics']['avg_cpu_usage']:.1f}%
                                    </div>
                                    <div class="metric-card">
                                        <strong>Avg Memory Usage</strong><br>
                                        {exp['chaos_impact_metrics']['avg_memory_usage']:.1f}%
                                    </div>
                                </div>
                            </div>
                        </div>
            """
            
            if exp['issues_discovered']:
                html_content += '<div class="issues-list"><h5>🚨 Issues Discovered</h5><ul>'
                for issue in exp['issues_discovered']:
                    html_content += f"<li>{issue}</li>"
                html_content += "</ul></div>"
            
            if exp['lessons_learned']:
                html_content += '<div class="lessons-list"><h5>💡 Lessons Learned</h5><ul>'
                for lesson in exp['lessons_learned']:
                    html_content += f"<li>{lesson}</li>"
                html_content += "</ul></div>"
            
            html_content += "</div>"
        
        html_content += """
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html_content)

    async def run_comprehensive_chaos_tests(self) -> Dict[str, Any]:
        test_results = await self.run_chaos_test_suite()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.results_dir / f"chaos_engineering_report_{timestamp}.json"
        
        self.generate_chaos_report(test_results, str(report_path))
        
        return {
            "test_results": test_results,
            "report_path": str(report_path),
            "html_report_path": str(report_path).replace('.json', '.html'),
            "summary": test_results["summary"]
        }

async def main():
    engine = ChaosEngineeringEngine()
    
    results = await engine.run_comprehensive_chaos_tests()
    
    print(f"\n{'='*60}")
    print(f"CHAOS ENGINEERING TESTS COMPLETED!")
    print(f"{'='*60}")
    print(f"Total experiments: {results['summary']['total_experiments']}")
    print(f"Success rate: {results['summary']['success_rate']:.1f}%")
    print(f"Recovery rate: {results['summary']['recovery_rate']:.1f}%")
    print(f"Hypothesis accuracy: {results['summary']['hypothesis_accuracy']:.1f}%")
    print(f"Resilience score: {results['summary']['resilience_score']:.1f}/100")
    print(f"Issues discovered: {results['summary']['total_issues_discovered']}")
    print(f"Lessons learned: {results['summary']['total_lessons_learned']}")
    print(f"Average recovery time: {results['summary']['average_recovery_time_seconds']:.1f}s")
    print(f"Report saved to: {results['report_path']}")
    print(f"HTML report saved to: {results['html_report_path']}")

if __name__ == "__main__":
    asyncio.run(main())