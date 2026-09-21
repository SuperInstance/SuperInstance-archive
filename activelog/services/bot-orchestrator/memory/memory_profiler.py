"""
Advanced Memory Profiling and Monitoring Tools
World-class memory profiler with deep insights and real-time monitoring
"""

import asyncio
import gc
import logging
import psutil
import sys
import threading
import time
import tracemalloc
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable, Union, Tuple
import json
import sqlite3
import uuid
import pickle
import linecache
import traceback
from functools import wraps
import weakref
import os
import mmap
import resource

logger = logging.getLogger(__name__)


class ProfilingLevel(Enum):
    """Memory profiling detail levels"""
    BASIC = "basic"           # Basic memory stats
    DETAILED = "detailed"     # Object-level tracking
    COMPREHENSIVE = "comprehensive"  # Full stack traces and references
    REAL_TIME = "real_time"   # Continuous real-time monitoring


class MemoryEventType(Enum):
    """Types of memory events to track"""
    ALLOCATION = "allocation"
    DEALLOCATION = "deallocation"
    GROWTH = "growth"
    SHRINKAGE = "shrinkage"
    GC_COLLECTION = "gc_collection"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    SWAP_IN = "swap_in"
    SWAP_OUT = "swap_out"
    MEMORY_LEAK = "memory_leak"
    FRAGMENTATION = "fragmentation"


@dataclass
class StackFrame:
    """Stack frame information"""
    filename: str
    function_name: str
    line_number: int
    code_line: str = ""
    
    def __post_init__(self):
        if not self.code_line:
            try:
                self.code_line = linecache.getline(self.filename, self.line_number).strip()
            except:
                self.code_line = ""


@dataclass
class MemoryAllocation:
    """Detailed memory allocation record"""
    allocation_id: str
    size: int
    timestamp: datetime
    stack_trace: List[StackFrame]
    object_type: str
    still_allocated: bool = True
    deallocated_at: Optional[datetime] = None
    peak_size: int = 0
    
    def __post_init__(self):
        self.peak_size = max(self.peak_size, self.size)


@dataclass
class ObjectReference:
    """Object reference tracking"""
    object_id: str
    object_type: str
    size: int
    reference_count: int
    referrers: List[str] = field(default_factory=list)
    referents: List[str] = field(default_factory=list)
    creation_time: datetime = field(default_factory=datetime.now)
    last_access_time: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    is_circular: bool = False


@dataclass
class MemorySnapshot:
    """Complete memory snapshot at a point in time"""
    snapshot_id: str
    timestamp: datetime
    total_memory: int
    heap_size: int
    stack_size: int
    
    # Memory breakdown
    memory_by_type: Dict[str, int] = field(default_factory=dict)
    memory_by_module: Dict[str, int] = field(default_factory=dict)
    memory_by_function: Dict[str, int] = field(default_factory=dict)
    
    # Top allocations
    top_allocations: List[MemoryAllocation] = field(default_factory=list)
    
    # Statistics
    total_allocations: int = 0
    active_allocations: int = 0
    gc_stats: Dict[str, Any] = field(default_factory=dict)
    
    # Comparison with previous snapshot
    growth_since_last: int = 0
    new_allocations: int = 0
    freed_allocations: int = 0


@dataclass
class LeakDetectionResult:
    """Memory leak detection results"""
    leak_id: str
    severity: str  # "minor", "moderate", "severe", "critical"
    description: str
    suspected_objects: List[ObjectReference]
    growth_rate: float  # bytes per second
    leak_duration: timedelta
    stack_traces: List[List[StackFrame]]
    confidence: float  # 0.0 to 1.0
    recommendations: List[str]
    detected_at: datetime = field(default_factory=datetime.now)


class AdvancedMemoryProfiler:
    """World-class memory profiler with comprehensive analysis capabilities"""
    
    def __init__(
        self,
        profiling_level: ProfilingLevel = ProfilingLevel.DETAILED,
        max_snapshots: int = 100,
        snapshot_interval: int = 60,  # seconds
        leak_detection_threshold: float = 1024 * 1024,  # 1MB growth
        db_path: str = "/home/activeloguser/activelog/data/memory_profiler.db"
    ):
        self.profiling_level = profiling_level
        self.max_snapshots = max_snapshots
        self.snapshot_interval = snapshot_interval
        self.leak_detection_threshold = leak_detection_threshold
        self.db_path = db_path
        
        # Profiling data
        self.snapshots: deque = deque(maxlen=max_snapshots)
        self.allocations: Dict[str, MemoryAllocation] = {}
        self.object_references: Dict[str, ObjectReference] = {}
        self.memory_events: deque = deque(maxlen=10000)
        self.leak_reports: Dict[str, LeakDetectionResult] = {}
        
        # Tracking state
        self.profiling_active = False
        self.start_time = datetime.now()
        self.baseline_memory = 0
        
        # Background tasks
        self.running = False
        self.profiler_task = None
        self.leak_detector_task = None
        self.snapshot_task = None
        
        # Statistics
        self.total_snapshots_taken = 0
        self.leaks_detected = 0
        self.memory_optimizations = 0
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Weak references for object tracking
        self.tracked_objects = weakref.WeakSet()
        
        # Initialize system
        self._init_database()
        self._setup_profiling()
    
    def _init_database(self):
        """Initialize profiling database"""
        with sqlite3.connect(self.db_path) as conn:
            # Memory snapshots
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    snapshot_data TEXT NOT NULL
                )
            """)
            
            # Memory allocations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_allocations (
                    allocation_id TEXT PRIMARY KEY,
                    size INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    object_type TEXT NOT NULL,
                    stack_trace TEXT NOT NULL,
                    still_allocated BOOLEAN DEFAULT TRUE,
                    deallocated_at TEXT
                )
            """)
            
            # Memory events
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    memory_before INTEGER,
                    memory_after INTEGER,
                    entity_id TEXT,
                    event_data TEXT
                )
            """)
            
            # Leak detection results
            conn.execute("""
                CREATE TABLE IF NOT EXISTS leak_detection (
                    leak_id TEXT PRIMARY KEY,
                    severity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    growth_rate REAL NOT NULL,
                    leak_duration INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    detected_at TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    leak_data TEXT NOT NULL
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON memory_snapshots(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_allocations_timestamp ON memory_allocations(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON memory_events(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_leaks_detected ON leak_detection(detected_at)")
    
    def _setup_profiling(self):
        """Setup memory profiling based on level"""
        if self.profiling_level in [ProfilingLevel.DETAILED, ProfilingLevel.COMPREHENSIVE]:
            if not tracemalloc.is_tracing():
                tracemalloc.start(25)  # Store up to 25 frames
        
        # Set memory usage limits for monitoring
        try:
            # Set soft limit for memory monitoring
            soft_limit = 4 * 1024 * 1024 * 1024  # 4GB
            resource.setrlimit(resource.RLIMIT_AS, (soft_limit, resource.RLIM_INFINITY))
        except:
            pass  # May fail on some systems
    
    def start_profiling(self):
        """Start memory profiling"""
        if not self.profiling_active:
            self.profiling_active = True
            self.running = True
            self.start_time = datetime.now()
            
            # Get baseline memory
            process = psutil.Process()
            self.baseline_memory = process.memory_info().rss
            
            # Start background tasks
            if self.profiling_level == ProfilingLevel.REAL_TIME:
                self.profiler_task = threading.Thread(target=self._real_time_profiler, daemon=True)
                self.profiler_task.start()
            
            self.leak_detector_task = threading.Thread(target=self._leak_detector, daemon=True)
            self.snapshot_task = threading.Thread(target=self._snapshot_manager, daemon=True)
            
            self.leak_detector_task.start()
            self.snapshot_task.start()
            
            logger.info("Memory profiling started")
    
    def stop_profiling(self):
        """Stop memory profiling"""
        if self.profiling_active:
            self.profiling_active = False
            self.running = False
            
            # Wait for background tasks
            for task in [self.profiler_task, self.leak_detector_task, self.snapshot_task]:
                if task and task.is_alive():
                    task.join(timeout=5)
            
            # Take final snapshot
            final_snapshot = self.take_memory_snapshot("profiling_end")
            if final_snapshot:
                self.snapshots.append(final_snapshot)
                self._persist_snapshot(final_snapshot)
            
            logger.info("Memory profiling stopped")
    
    def take_memory_snapshot(self, reason: str = "manual") -> MemorySnapshot:
        """Take a comprehensive memory snapshot"""
        try:
            snapshot_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            # Get process memory info
            process = psutil.Process()
            memory_info = process.memory_info()
            
            snapshot = MemorySnapshot(
                snapshot_id=snapshot_id,
                timestamp=timestamp,
                total_memory=memory_info.rss,
                heap_size=memory_info.rss - memory_info.vms if hasattr(memory_info, 'vms') else memory_info.rss,
                stack_size=0  # Will be calculated
            )
            
            # Detailed analysis based on profiling level
            if self.profiling_level in [ProfilingLevel.DETAILED, ProfilingLevel.COMPREHENSIVE]:
                self._analyze_memory_detailed(snapshot)
            else:
                self._analyze_memory_basic(snapshot)
            
            # Compare with previous snapshot
            if self.snapshots:
                self._compare_with_previous(snapshot, self.snapshots[-1])
            
            # Garbage collection stats
            snapshot.gc_stats = {
                "collections": gc.get_count(),
                "objects": len(gc.get_objects()),
                "referrers": len(gc.get_referrers(*gc.get_objects()[:100])) if gc.get_objects() else 0
            }
            
            self.total_snapshots_taken += 1
            
            # Record event
            self._record_event(MemoryEventType.GROWTH if snapshot.growth_since_last > 0 else MemoryEventType.SHRINKAGE,
                             memory_before=self.snapshots[-1].total_memory if self.snapshots else 0,
                             memory_after=snapshot.total_memory,
                             event_data={"reason": reason, "snapshot_id": snapshot_id})
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error taking memory snapshot: {e}")
            return None
    
    def _analyze_memory_detailed(self, snapshot: MemorySnapshot):
        """Perform detailed memory analysis"""
        if not tracemalloc.is_tracing():
            return
        
        try:
            # Get current traces
            current_traces = tracemalloc.get_traced_memory()
            snapshot.heap_size = current_traces[0]
            
            # Get top allocations
            top_stats = tracemalloc.take_snapshot().statistics('traceback')[:50]
            
            for stat in top_stats:
                # Create stack trace
                stack_frames = []
                for frame in stat.traceback:
                    stack_frame = StackFrame(
                        filename=frame.filename,
                        function_name="",  # Not available in tracemalloc
                        line_number=frame.lineno
                    )
                    stack_frames.append(stack_frame)
                
                # Create allocation record
                allocation = MemoryAllocation(
                    allocation_id=str(uuid.uuid4()),
                    size=stat.size,
                    timestamp=snapshot.timestamp,
                    stack_trace=stack_frames,
                    object_type="unknown",  # Would need additional introspection
                    peak_size=stat.size
                )
                
                snapshot.top_allocations.append(allocation)
                
                # Update memory breakdown
                module = os.path.basename(stack_frames[0].filename) if stack_frames else "unknown"
                snapshot.memory_by_module[module] = snapshot.memory_by_module.get(module, 0) + stat.size
            
            # Analyze object types
            for obj in gc.get_objects()[:1000]:  # Sample first 1000 objects
                obj_type = type(obj).__name__
                obj_size = sys.getsizeof(obj)
                snapshot.memory_by_type[obj_type] = snapshot.memory_by_type.get(obj_type, 0) + obj_size
            
            snapshot.total_allocations = len(top_stats)
            snapshot.active_allocations = len([s for s in top_stats if s.size > 0])
            
        except Exception as e:
            logger.error(f"Error in detailed memory analysis: {e}")
    
    def _analyze_memory_basic(self, snapshot: MemorySnapshot):
        """Perform basic memory analysis"""
        try:
            # Basic object type counting
            type_counts = defaultdict(int)
            type_sizes = defaultdict(int)
            
            for obj in gc.get_objects()[:5000]:  # Sample more objects for basic analysis
                obj_type = type(obj).__name__
                obj_size = sys.getsizeof(obj)
                type_counts[obj_type] += 1
                type_sizes[obj_type] += obj_size
            
            snapshot.memory_by_type = dict(type_sizes)
            snapshot.total_allocations = sum(type_counts.values())
            snapshot.active_allocations = len(type_counts)
            
        except Exception as e:
            logger.error(f"Error in basic memory analysis: {e}")
    
    def _compare_with_previous(self, current: MemorySnapshot, previous: MemorySnapshot):
        """Compare current snapshot with previous"""
        current.growth_since_last = current.total_memory - previous.total_memory
        
        # Calculate new and freed allocations (simplified)
        current.new_allocations = max(0, current.total_allocations - previous.total_allocations)
        current.freed_allocations = max(0, previous.total_allocations - current.total_allocations)
    
    def detect_memory_leaks(self) -> List[LeakDetectionResult]:
        """Detect potential memory leaks"""
        leaks = []
        
        if len(self.snapshots) < 3:  # Need at least 3 snapshots
            return leaks
        
        try:
            # Analyze memory growth patterns
            recent_snapshots = list(self.snapshots)[-10:]  # Last 10 snapshots
            
            # Calculate growth rate
            time_span = (recent_snapshots[-1].timestamp - recent_snapshots[0].timestamp).total_seconds()
            if time_span == 0:
                return leaks
            
            memory_growth = recent_snapshots[-1].total_memory - recent_snapshots[0].total_memory
            growth_rate = memory_growth / time_span
            
            if growth_rate > self.leak_detection_threshold:
                # Potential leak detected
                leak_id = str(uuid.uuid4())
                
                # Analyze which object types are growing
                growing_types = {}
                for snapshot in recent_snapshots:
                    for obj_type, size in snapshot.memory_by_type.items():
                        if obj_type not in growing_types:
                            growing_types[obj_type] = []
                        growing_types[obj_type].append(size)
                
                # Find types with consistent growth
                suspicious_types = []
                for obj_type, sizes in growing_types.items():
                    if len(sizes) >= 3:
                        type_growth = sizes[-1] - sizes[0]
                        if type_growth > 0:
                            suspicious_types.append((obj_type, type_growth))
                
                # Create leak report
                leak = LeakDetectionResult(
                    leak_id=leak_id,
                    severity=self._classify_leak_severity(growth_rate),
                    description=f"Memory growth detected: {growth_rate/1024/1024:.2f} MB/s",
                    suspected_objects=[],  # Would need more detailed analysis
                    growth_rate=growth_rate,
                    leak_duration=timedelta(seconds=time_span),
                    stack_traces=[],
                    confidence=min(0.9, growth_rate / (10 * 1024 * 1024)),  # Higher confidence for faster growth
                    recommendations=self._generate_leak_recommendations(growth_rate, suspicious_types)
                )
                
                leaks.append(leak)
                self.leak_reports[leak_id] = leak
                self._persist_leak_detection(leak)
                self.leaks_detected += 1
                
                logger.warning(f"Memory leak detected: {leak.description}")
        
        except Exception as e:
            logger.error(f"Error in leak detection: {e}")
        
        return leaks
    
    def _classify_leak_severity(self, growth_rate: float) -> str:
        """Classify leak severity based on growth rate"""
        mb_per_sec = growth_rate / 1024 / 1024
        
        if mb_per_sec > 10:
            return "critical"
        elif mb_per_sec > 5:
            return "severe"
        elif mb_per_sec > 1:
            return "moderate"
        else:
            return "minor"
    
    def _generate_leak_recommendations(self, growth_rate: float, suspicious_types: List[Tuple[str, int]]) -> List[str]:
        """Generate recommendations for addressing memory leaks"""
        recommendations = []
        
        if growth_rate > 10 * 1024 * 1024:  # > 10MB/s
            recommendations.append("Critical memory leak - immediate investigation required")
            recommendations.append("Consider restarting the affected service")
        
        if suspicious_types:
            top_types = sorted(suspicious_types, key=lambda x: x[1], reverse=True)[:3]
            for obj_type, growth in top_types:
                recommendations.append(f"Investigate {obj_type} objects - growing by {growth/1024:.1f} KB")
        
        recommendations.extend([
            "Review recent code changes that might cause memory retention",
            "Check for circular references in object relationships",
            "Consider implementing object pooling for frequently created objects",
            "Run garbage collection manually to see if memory is freed",
            "Use memory profiler to identify specific allocation patterns"
        ])
        
        return recommendations
    
    def profile_function(self, func: Callable) -> Callable:
        """Decorator to profile memory usage of a function"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self.profiling_active:
                return func(*args, **kwargs)
            
            # Take snapshot before
            snapshot_before = None
            if tracemalloc.is_tracing():
                snapshot_before = tracemalloc.take_snapshot()
            
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Take snapshot after
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss
                
                if snapshot_before and tracemalloc.is_tracing():
                    snapshot_after = tracemalloc.take_snapshot()
                    top_stats = snapshot_after.compare_to(snapshot_before, 'traceback')[:10]
                    
                    # Log top memory changes
                    for stat in top_stats:
                        if stat.size_diff > 1024:  # Only log changes > 1KB
                            logger.debug(f"Memory change in {func.__name__}: {stat.size_diff:+,} bytes at {stat.traceback}")
                
                # Record profiling data
                memory_diff = end_memory - start_memory
                execution_time = end_time - start_time
                
                self._record_function_profile(func.__name__, memory_diff, execution_time, args, kwargs)
                
                return result
                
            except Exception as e:
                # Record error in profiling
                self._record_function_error(func.__name__, str(e))
                raise
        
        return wrapper
    
    def track_object_lifecycle(self, obj: Any, object_id: Optional[str] = None) -> str:
        """Track the lifecycle of a specific object"""
        if object_id is None:
            object_id = str(uuid.uuid4())
        
        try:
            # Create object reference
            obj_ref = ObjectReference(
                object_id=object_id,
                object_type=type(obj).__name__,
                size=sys.getsizeof(obj),
                reference_count=sys.getrefcount(obj)
            )
            
            # Find referrers and referents
            if self.profiling_level == ProfilingLevel.COMPREHENSIVE:
                referrers = gc.get_referrers(obj)
                referents = gc.get_referents(obj)
                
                obj_ref.referrers = [str(type(r)) for r in referrers[:10]]  # Top 10
                obj_ref.referents = [str(type(r)) for r in referents[:10]]
                
                # Check for circular references
                obj_ref.is_circular = obj in referents
            
            self.object_references[object_id] = obj_ref
            
            # Add to weak reference set for tracking
            try:
                self.tracked_objects.add(obj)
            except TypeError:
                # Object may not support weak references
                pass
            
            return object_id
            
        except Exception as e:
            logger.error(f"Error tracking object lifecycle: {e}")
            return object_id
    
    def get_memory_hotspots(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Identify memory hotspots in the code"""
        hotspots = []
        
        if not self.snapshots:
            return hotspots
        
        try:
            latest_snapshot = self.snapshots[-1]
            
            # Get hotspots by module
            module_hotspots = []
            for module, size in latest_snapshot.memory_by_module.items():
                module_hotspots.append({
                    "type": "module",
                    "name": module,
                    "memory_usage": size,
                    "percentage": (size / latest_snapshot.total_memory) * 100 if latest_snapshot.total_memory > 0 else 0
                })
            
            # Get hotspots by object type
            type_hotspots = []
            for obj_type, size in latest_snapshot.memory_by_type.items():
                type_hotspots.append({
                    "type": "object_type",
                    "name": obj_type,
                    "memory_usage": size,
                    "percentage": (size / latest_snapshot.total_memory) * 100 if latest_snapshot.total_memory > 0 else 0
                })
            
            # Combine and sort
            all_hotspots = module_hotspots + type_hotspots
            all_hotspots.sort(key=lambda x: x["memory_usage"], reverse=True)
            
            hotspots = all_hotspots[:limit]
            
        except Exception as e:
            logger.error(f"Error getting memory hotspots: {e}")
        
        return hotspots
    
    def generate_memory_report(self) -> Dict[str, Any]:
        """Generate comprehensive memory profiling report"""
        try:
            # Basic statistics
            current_memory = psutil.Process().memory_info().rss
            profiling_duration = (datetime.now() - self.start_time).total_seconds()
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "profiling_duration_seconds": profiling_duration,
                "profiling_level": self.profiling_level.value,
                "baseline_memory": self.baseline_memory,
                "current_memory": current_memory,
                "memory_growth": current_memory - self.baseline_memory,
                "total_snapshots": self.total_snapshots_taken,
                "leaks_detected": self.leaks_detected,
                "memory_optimizations": self.memory_optimizations
            }
            
            # Latest snapshot data
            if self.snapshots:
                latest = self.snapshots[-1]
                report["latest_snapshot"] = {
                    "timestamp": latest.timestamp.isoformat(),
                    "total_memory": latest.total_memory,
                    "heap_size": latest.heap_size,
                    "active_allocations": latest.active_allocations,
                    "gc_stats": latest.gc_stats
                }
                
                # Memory breakdown
                report["memory_by_type"] = dict(latest.memory_by_type)
                report["memory_by_module"] = dict(latest.memory_by_module)
            
            # Memory hotspots
            report["memory_hotspots"] = self.get_memory_hotspots(10)
            
            # Leak detection results
            active_leaks = [leak for leak in self.leak_reports.values()]
            report["memory_leaks"] = [
                {
                    "leak_id": leak.leak_id,
                    "severity": leak.severity,
                    "description": leak.description,
                    "growth_rate_mb_per_sec": leak.growth_rate / 1024 / 1024,
                    "confidence": leak.confidence,
                    "recommendations": leak.recommendations[:3]  # Top 3
                }
                for leak in active_leaks[-5:]  # Last 5 leaks
            ]
            
            # Memory trends
            if len(self.snapshots) > 1:
                memory_trend = []
                for snapshot in list(self.snapshots)[-20:]:  # Last 20 snapshots
                    memory_trend.append({
                        "timestamp": snapshot.timestamp.isoformat(),
                        "memory": snapshot.total_memory,
                        "growth": snapshot.growth_since_last
                    })
                report["memory_trend"] = memory_trend
            
            # Recommendations
            report["recommendations"] = self._generate_optimization_recommendations()
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating memory report: {e}")
            return {"error": str(e)}
    
    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate memory optimization recommendations"""
        recommendations = []
        
        if not self.snapshots:
            return recommendations
        
        try:
            latest = self.snapshots[-1]
            
            # Check for high memory usage
            current_memory_mb = latest.total_memory / 1024 / 1024
            if current_memory_mb > 1000:  # > 1GB
                recommendations.append("High memory usage detected - consider implementing memory pooling")
            
            # Check for object type concentrations
            if latest.memory_by_type:
                top_type = max(latest.memory_by_type.items(), key=lambda x: x[1])
                type_percentage = (top_type[1] / latest.total_memory) * 100
                if type_percentage > 30:
                    recommendations.append(f"High concentration of {top_type[0]} objects ({type_percentage:.1f}%) - review object lifecycle")
            
            # Check for rapid growth
            if len(self.snapshots) >= 2:
                recent_growth = sum(s.growth_since_last for s in list(self.snapshots)[-5:])
                if recent_growth > 100 * 1024 * 1024:  # > 100MB growth
                    recommendations.append("Rapid memory growth detected - investigate recent allocations")
            
            # Check garbage collection efficiency
            if latest.gc_stats.get("objects", 0) > 100000:
                recommendations.append("High object count - consider implementing object pooling or more frequent cleanup")
            
            # General recommendations
            recommendations.extend([
                "Implement caching with TTL to prevent indefinite memory growth",
                "Use generators and iterators for processing large datasets",
                "Consider using memory-mapped files for large data structures",
                "Implement periodic cleanup routines for temporary objects"
            ])
            
        except Exception as e:
            logger.error(f"Error generating optimization recommendations: {e}")
        
        return recommendations[:10]  # Top 10 recommendations
    
    def _real_time_profiler(self):
        """Real-time memory profiling task"""
        while self.running:
            try:
                # Take frequent snapshots
                snapshot = self.take_memory_snapshot("real_time")
                if snapshot:
                    self.snapshots.append(snapshot)
                    
                    # Persist important snapshots
                    if self.total_snapshots_taken % 10 == 0:
                        self._persist_snapshot(snapshot)
                
                # Real-time leak detection
                if len(self.snapshots) >= 5:
                    leaks = self.detect_memory_leaks()
                    for leak in leaks:
                        if leak.severity in ["severe", "critical"]:
                            logger.critical(f"Critical memory leak detected: {leak.description}")
                
                time.sleep(5)  # Real-time monitoring every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in real-time profiler: {e}")
                time.sleep(30)
    
    def _leak_detector(self):
        """Background leak detection task"""
        while self.running:
            try:
                if len(self.snapshots) >= 3:
                    self.detect_memory_leaks()
                
                time.sleep(300)  # Check for leaks every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in leak detector: {e}")
                time.sleep(300)
    
    def _snapshot_manager(self):
        """Background snapshot management task"""
        while self.running:
            try:
                # Take periodic snapshots
                if self.profiling_level != ProfilingLevel.REAL_TIME:
                    snapshot = self.take_memory_snapshot("periodic")
                    if snapshot:
                        self.snapshots.append(snapshot)
                        self._persist_snapshot(snapshot)
                
                # Cleanup old data
                self._cleanup_old_profiling_data()
                
                time.sleep(self.snapshot_interval)
                
            except Exception as e:
                logger.error(f"Error in snapshot manager: {e}")
                time.sleep(self.snapshot_interval)
    
    def _record_event(self, event_type: MemoryEventType, memory_before: int = 0, memory_after: int = 0, entity_id: str = "", event_data: Dict[str, Any] = None):
        """Record a memory event"""
        event = {
            "event_type": event_type.value,
            "timestamp": datetime.now(),
            "memory_before": memory_before,
            "memory_after": memory_after,
            "entity_id": entity_id,
            "event_data": event_data or {}
        }
        
        self.memory_events.append(event)
        
        # Persist important events
        if event_type in [MemoryEventType.MEMORY_LEAK, MemoryEventType.GC_COLLECTION]:
            self._persist_event(event)
    
    def _record_function_profile(self, func_name: str, memory_diff: int, execution_time: float, args: tuple, kwargs: dict):
        """Record function profiling data"""
        profile_data = {
            "function_name": func_name,
            "memory_diff": memory_diff,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
            "args_count": len(args),
            "kwargs_count": len(kwargs)
        }
        
        # Store in memory events
        self._record_event(
            MemoryEventType.ALLOCATION if memory_diff > 0 else MemoryEventType.DEALLOCATION,
            memory_before=0,
            memory_after=abs(memory_diff),
            entity_id=func_name,
            event_data=profile_data
        )
    
    def _record_function_error(self, func_name: str, error: str):
        """Record function profiling error"""
        self._record_event(
            MemoryEventType.ALLOCATION,  # Use allocation as default
            entity_id=func_name,
            event_data={"error": error, "function_name": func_name}
        )
    
    def _cleanup_old_profiling_data(self):
        """Clean up old profiling data"""
        try:
            cutoff_date = datetime.now() - timedelta(days=7)
            
            # Clean up old events
            self.memory_events = deque([
                event for event in self.memory_events
                if event["timestamp"] > cutoff_date
            ], maxlen=10000)
            
            # Clean up old allocations
            expired_allocations = [
                alloc_id for alloc_id, alloc in self.allocations.items()
                if alloc.timestamp < cutoff_date
            ]
            
            for alloc_id in expired_allocations:
                del self.allocations[alloc_id]
            
            # Clean up old object references
            expired_refs = [
                ref_id for ref_id, ref in self.object_references.items()
                if ref.creation_time < cutoff_date
            ]
            
            for ref_id in expired_refs:
                del self.object_references[ref_id]
                
        except Exception as e:
            logger.error(f"Error cleaning up profiling data: {e}")
    
    def _persist_snapshot(self, snapshot: MemorySnapshot):
        """Persist snapshot to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                snapshot_data = {
                    "total_memory": snapshot.total_memory,
                    "heap_size": snapshot.heap_size,
                    "stack_size": snapshot.stack_size,
                    "memory_by_type": snapshot.memory_by_type,
                    "memory_by_module": snapshot.memory_by_module,
                    "memory_by_function": snapshot.memory_by_function,
                    "total_allocations": snapshot.total_allocations,
                    "active_allocations": snapshot.active_allocations,
                    "gc_stats": snapshot.gc_stats,
                    "growth_since_last": snapshot.growth_since_last,
                    "new_allocations": snapshot.new_allocations,
                    "freed_allocations": snapshot.freed_allocations
                }
                
                conn.execute("""
                    INSERT INTO memory_snapshots (snapshot_id, timestamp, snapshot_data)
                    VALUES (?, ?, ?)
                """, (
                    snapshot.snapshot_id,
                    snapshot.timestamp.isoformat(),
                    json.dumps(snapshot_data)
                ))
        except Exception as e:
            logger.error(f"Error persisting snapshot: {e}")
    
    def _persist_leak_detection(self, leak: LeakDetectionResult):
        """Persist leak detection result"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                leak_data = {
                    "suspected_objects": [obj.__dict__ for obj in leak.suspected_objects],
                    "stack_traces": [[frame.__dict__ for frame in trace] for trace in leak.stack_traces],
                    "recommendations": leak.recommendations
                }
                
                conn.execute("""
                    INSERT INTO leak_detection (
                        leak_id, severity, description, growth_rate, leak_duration,
                        confidence, detected_at, leak_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    leak.leak_id,
                    leak.severity,
                    leak.description,
                    leak.growth_rate,
                    int(leak.leak_duration.total_seconds()),
                    leak.confidence,
                    leak.detected_at.isoformat(),
                    json.dumps(leak_data)
                ))
        except Exception as e:
            logger.error(f"Error persisting leak detection: {e}")
    
    def _persist_event(self, event: Dict[str, Any]):
        """Persist memory event to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO memory_events (
                        event_type, timestamp, memory_before, memory_after, entity_id, event_data
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    event["event_type"],
                    event["timestamp"].isoformat(),
                    event["memory_before"],
                    event["memory_after"],
                    event["entity_id"],
                    json.dumps(event["event_data"])
                ))
        except Exception as e:
            logger.error(f"Error persisting event: {e}")


# Factory function
def create_memory_profiler(
    level: str = "detailed",
    max_snapshots: int = 100,
    snapshot_interval: int = 60
) -> AdvancedMemoryProfiler:
    """Create advanced memory profiler with configuration"""
    profiling_level = ProfilingLevel(level)
    
    return AdvancedMemoryProfiler(
        profiling_level=profiling_level,
        max_snapshots=max_snapshots,
        snapshot_interval=snapshot_interval
    )