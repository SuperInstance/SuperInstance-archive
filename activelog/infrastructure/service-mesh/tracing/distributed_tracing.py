import time
import uuid
import json
import threading
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
from contextlib import contextmanager, asynccontextmanager
import contextvars


class SpanKind(Enum):
    SERVER = "server"      # Receiving a request
    CLIENT = "client"      # Making a request  
    PRODUCER = "producer"  # Producing messages
    CONSUMER = "consumer"  # Consuming messages
    INTERNAL = "internal"  # Internal computation


class SpanStatus(Enum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanContext:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = None
    
    def __post_init__(self):
        if self.baggage is None:
            self.baggage = {}


@dataclass
class SpanEvent:
    name: str
    timestamp: datetime
    attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


@dataclass
class SpanLink:
    trace_id: str
    span_id: str
    attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}


@dataclass 
class Span:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    kind: SpanKind = SpanKind.INTERNAL
    tags: Dict[str, Any] = None
    events: List[SpanEvent] = None
    links: List[SpanLink] = None
    baggage: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.events is None:
            self.events = []
        if self.links is None:
            self.links = []
        if self.baggage is None:
            self.baggage = {}
    
    def finish(self, status: SpanStatus = SpanStatus.OK):
        """Finish the span"""
        self.end_time = datetime.now()
        self.status = status
        
        if self.start_time and self.end_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
    
    def set_tag(self, key: str, value: Any):
        """Set a tag on the span"""
        self.tags[key] = value
    
    def add_event(self, name: str, attributes: Dict[str, Any] = None):
        """Add an event to the span"""
        event = SpanEvent(
            name=name,
            timestamp=datetime.now(),
            attributes=attributes or {}
        )
        self.events.append(event)
    
    def add_link(self, trace_id: str, span_id: str, attributes: Dict[str, Any] = None):
        """Add a link to another span"""
        link = SpanLink(
            trace_id=trace_id,
            span_id=span_id,
            attributes=attributes or {}
        )
        self.links.append(link)
    
    def set_baggage(self, key: str, value: str):
        """Set baggage item"""
        self.baggage[key] = value
    
    def get_baggage(self, key: str) -> Optional[str]:
        """Get baggage item"""
        return self.baggage.get(key)


class TraceContext:
    """Thread-local trace context storage"""
    
    def __init__(self):
        self._current_span = contextvars.ContextVar('current_span', default=None)
        self._current_trace = contextvars.ContextVar('current_trace', default=None)
    
    def get_current_span(self) -> Optional[Span]:
        """Get current active span"""
        return self._current_span.get()
    
    def set_current_span(self, span: Optional[Span]):
        """Set current active span"""
        self._current_span.set(span)
    
    def get_current_trace_id(self) -> Optional[str]:
        """Get current trace ID"""
        trace_id = self._current_trace.get()
        if trace_id:
            return trace_id
        
        current_span = self.get_current_span()
        if current_span:
            return current_span.trace_id
        
        return None
    
    def set_current_trace_id(self, trace_id: Optional[str]):
        """Set current trace ID"""
        self._current_trace.set(trace_id)


class SpanExporter:
    """Base class for span exporters"""
    
    def export(self, spans: List[Span]) -> bool:
        """Export spans to external system"""
        raise NotImplementedError
    
    def shutdown(self):
        """Shutdown the exporter"""
        pass


class ConsoleSpanExporter(SpanExporter):
    """Export spans to console for debugging"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def export(self, spans: List[Span]) -> bool:
        """Export spans to console"""
        for span in spans:
            self.logger.info(f"Trace: {span.trace_id[:8]}... | "
                           f"Span: {span.span_id[:8]}... | "
                           f"Service: {span.service_name} | "
                           f"Operation: {span.operation_name} | "
                           f"Duration: {span.duration_ms:.2f}ms | "
                           f"Status: {span.status.value}")
            
            if span.tags:
                self.logger.info(f"  Tags: {span.tags}")
            
            for event in span.events:
                self.logger.info(f"  Event: {event.name} at {event.timestamp}")
        
        return True


class MemorySpanExporter(SpanExporter):
    """In-memory span storage for testing and development"""
    
    def __init__(self, max_spans: int = 10000):
        self.spans = deque(maxlen=max_spans)
        self.lock = threading.RLock()
    
    def export(self, spans: List[Span]) -> bool:
        """Store spans in memory"""
        with self.lock:
            self.spans.extend(spans)
        return True
    
    def get_spans(self) -> List[Span]:
        """Get all stored spans"""
        with self.lock:
            return list(self.spans)
    
    def get_traces(self) -> Dict[str, List[Span]]:
        """Get spans grouped by trace ID"""
        with self.lock:
            traces = defaultdict(list)
            for span in self.spans:
                traces[span.trace_id].append(span)
            return dict(traces)
    
    def clear(self):
        """Clear all spans"""
        with self.lock:
            self.spans.clear()


class BatchSpanProcessor:
    """Batch processor for exporting spans"""
    
    def __init__(self, exporter: SpanExporter, 
                 max_queue_size: int = 2048,
                 batch_timeout: float = 5.0,
                 max_batch_size: int = 512):
        self.exporter = exporter
        self.max_queue_size = max_queue_size
        self.batch_timeout = batch_timeout
        self.max_batch_size = max_batch_size
        
        self.queue = deque()
        self.queue_lock = threading.RLock()
        self.worker_thread = None
        self.running = False
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Start the batch processor"""
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            self.logger.info("Batch span processor started")
    
    def stop(self):
        """Stop the batch processor"""
        if self.running:
            self.running = False
            if self.worker_thread:
                self.worker_thread.join(timeout=5)
            
            # Export any remaining spans
            self._export_batch()
            self.exporter.shutdown()
            self.logger.info("Batch span processor stopped")
    
    def on_end(self, span: Span):
        """Called when a span ends"""
        with self.queue_lock:
            if len(self.queue) < self.max_queue_size:
                self.queue.append(span)
            else:
                self.logger.warning("Span queue full, dropping span")
    
    def _worker_loop(self):
        """Worker thread loop for batch processing"""
        last_export = time.time()
        
        while self.running:
            current_time = time.time()
            should_export = False
            
            with self.queue_lock:
                queue_size = len(self.queue)
                
                # Check if we should export
                if (queue_size >= self.max_batch_size or 
                    (queue_size > 0 and current_time - last_export >= self.batch_timeout)):
                    should_export = True
            
            if should_export:
                self._export_batch()
                last_export = current_time
            
            time.sleep(0.1)  # Short sleep to prevent busy waiting
    
    def _export_batch(self):
        """Export a batch of spans"""
        batch = []
        
        with self.queue_lock:
            # Get a batch of spans
            batch_size = min(self.max_batch_size, len(self.queue))
            for _ in range(batch_size):
                if self.queue:
                    batch.append(self.queue.popleft())
        
        if batch:
            try:
                success = self.exporter.export(batch)
                if not success:
                    self.logger.error(f"Failed to export batch of {len(batch)} spans")
            except Exception as e:
                self.logger.error(f"Error exporting spans: {e}")


class Tracer:
    """Main tracer class for creating and managing spans"""
    
    def __init__(self, service_name: str, processor: BatchSpanProcessor):
        self.service_name = service_name
        self.processor = processor
        self.context = TraceContext()
        self.logger = logging.getLogger(__name__)
    
    def start_span(self, operation_name: str, 
                   parent: Optional[Span] = None,
                   kind: SpanKind = SpanKind.INTERNAL,
                   tags: Dict[str, Any] = None) -> Span:
        """Start a new span"""
        
        # Get trace context
        current_span = self.context.get_current_span()
        parent_span = parent or current_span
        
        # Generate IDs
        if parent_span:
            trace_id = parent_span.trace_id
            parent_span_id = parent_span.span_id
        else:
            trace_id = self._generate_trace_id()
            parent_span_id = None
        
        span_id = self._generate_span_id()
        
        # Create span
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=self.service_name,
            start_time=datetime.now(),
            kind=kind,
            tags=tags or {}
        )
        
        # Copy baggage from parent
        if parent_span and parent_span.baggage:
            span.baggage.update(parent_span.baggage)
        
        return span
    
    def _generate_trace_id(self) -> str:
        """Generate a new trace ID"""
        return uuid.uuid4().hex
    
    def _generate_span_id(self) -> str:
        """Generate a new span ID"""
        return uuid.uuid4().hex[:16]
    
    def finish_span(self, span: Span, status: SpanStatus = SpanStatus.OK):
        """Finish a span"""
        span.finish(status)
        self.processor.on_end(span)
    
    @contextmanager
    def span(self, operation_name: str, 
             kind: SpanKind = SpanKind.INTERNAL,
             tags: Dict[str, Any] = None):
        """Context manager for creating spans"""
        span = self.start_span(operation_name, kind=kind, tags=tags)
        
        # Set as current span
        old_span = self.context.get_current_span()
        self.context.set_current_span(span)
        
        try:
            yield span
            self.finish_span(span, SpanStatus.OK)
        except Exception as e:
            span.set_tag("error", True)
            span.set_tag("error.message", str(e))
            span.add_event("error", {"error.message": str(e)})
            self.finish_span(span, SpanStatus.ERROR)
            raise
        finally:
            # Restore previous span
            self.context.set_current_span(old_span)
    
    @asynccontextmanager
    async def async_span(self, operation_name: str,
                        kind: SpanKind = SpanKind.INTERNAL,
                        tags: Dict[str, Any] = None):
        """Async context manager for creating spans"""
        span = self.start_span(operation_name, kind=kind, tags=tags)
        
        # Set as current span
        old_span = self.context.get_current_span()
        self.context.set_current_span(span)
        
        try:
            yield span
            self.finish_span(span, SpanStatus.OK)
        except Exception as e:
            span.set_tag("error", True)
            span.set_tag("error.message", str(e))
            span.add_event("error", {"error.message": str(e)})
            self.finish_span(span, SpanStatus.ERROR)
            raise
        finally:
            # Restore previous span
            self.context.set_current_span(old_span)
    
    def inject_headers(self, headers: Dict[str, str], span: Optional[Span] = None) -> Dict[str, str]:
        """Inject trace context into HTTP headers"""
        target_span = span or self.context.get_current_span()
        if not target_span:
            return headers
        
        headers = headers.copy()
        headers['X-Trace-ID'] = target_span.trace_id
        headers['X-Span-ID'] = target_span.span_id
        
        # Inject baggage
        for key, value in target_span.baggage.items():
            headers[f'X-Baggage-{key}'] = value
        
        return headers
    
    def extract_headers(self, headers: Dict[str, str]) -> Optional[SpanContext]:
        """Extract trace context from HTTP headers"""
        trace_id = headers.get('X-Trace-ID')
        span_id = headers.get('X-Span-ID')
        
        if not trace_id:
            return None
        
        # Extract baggage
        baggage = {}
        for key, value in headers.items():
            if key.startswith('X-Baggage-'):
                baggage_key = key[10:]  # Remove 'X-Baggage-' prefix
                baggage[baggage_key] = value
        
        return SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            baggage=baggage
        )
    
    def start_span_from_context(self, operation_name: str, 
                               context: SpanContext,
                               kind: SpanKind = SpanKind.SERVER,
                               tags: Dict[str, Any] = None) -> Span:
        """Start a span from extracted context"""
        span = Span(
            trace_id=context.trace_id,
            span_id=self._generate_span_id(),
            parent_span_id=context.span_id,
            operation_name=operation_name,
            service_name=self.service_name,
            start_time=datetime.now(),
            kind=kind,
            tags=tags or {},
            baggage=context.baggage.copy()
        )
        
        return span


class DistributedTracer:
    """Global distributed tracing manager"""
    
    def __init__(self):
        self.tracers: Dict[str, Tracer] = {}
        self.processors: Dict[str, BatchSpanProcessor] = {}
        self.logger = logging.getLogger(__name__)
    
    def get_tracer(self, service_name: str, 
                   exporter: SpanExporter = None) -> Tracer:
        """Get or create a tracer for a service"""
        if service_name not in self.tracers:
            # Create exporter if not provided
            if exporter is None:
                exporter = ConsoleSpanExporter()
            
            # Create processor
            processor = BatchSpanProcessor(exporter)
            processor.start()
            
            # Create tracer
            tracer = Tracer(service_name, processor)
            
            self.tracers[service_name] = tracer
            self.processors[service_name] = processor
            
            self.logger.info(f"Created tracer for service: {service_name}")
        
        return self.tracers[service_name]
    
    def shutdown(self):
        """Shutdown all tracers and processors"""
        for processor in self.processors.values():
            processor.stop()
        
        self.tracers.clear()
        self.processors.clear()
        
        self.logger.info("Distributed tracer shutdown complete")


class TraceAnalyzer:
    """Analyze traces for performance and dependency insights"""
    
    def __init__(self, spans: List[Span]):
        self.spans = spans
        self.traces = self._group_by_trace()
    
    def _group_by_trace(self) -> Dict[str, List[Span]]:
        """Group spans by trace ID"""
        traces = defaultdict(list)
        for span in self.spans:
            traces[span.trace_id].append(span)
        
        # Sort spans in each trace by start time
        for trace_spans in traces.values():
            trace_spans.sort(key=lambda s: s.start_time)
        
        return dict(traces)
    
    def get_trace_statistics(self) -> Dict[str, Any]:
        """Get trace statistics"""
        if not self.traces:
            return {}
        
        trace_durations = []
        span_counts = []
        service_counts = defaultdict(int)
        operation_counts = defaultdict(int)
        
        for trace_spans in self.traces.values():
            # Calculate trace duration (from first start to last end)
            start_times = [s.start_time for s in trace_spans]
            end_times = [s.end_time for s in trace_spans if s.end_time]
            
            if start_times and end_times:
                trace_duration = (max(end_times) - min(start_times)).total_seconds() * 1000
                trace_durations.append(trace_duration)
            
            span_counts.append(len(trace_spans))
            
            # Count services and operations
            for span in trace_spans:
                service_counts[span.service_name] += 1
                operation_counts[span.operation_name] += 1
        
        return {
            "total_traces": len(self.traces),
            "total_spans": len(self.spans),
            "avg_trace_duration_ms": sum(trace_durations) / len(trace_durations) if trace_durations else 0,
            "avg_spans_per_trace": sum(span_counts) / len(span_counts) if span_counts else 0,
            "services": dict(service_counts),
            "operations": dict(operation_counts)
        }
    
    def find_slow_traces(self, percentile: float = 95.0) -> List[Tuple[str, float]]:
        """Find slowest traces"""
        trace_durations = []
        
        for trace_id, trace_spans in self.traces.items():
            start_times = [s.start_time for s in trace_spans]
            end_times = [s.end_time for s in trace_spans if s.end_time]
            
            if start_times and end_times:
                trace_duration = (max(end_times) - min(start_times)).total_seconds() * 1000
                trace_durations.append((trace_id, trace_duration))
        
        if not trace_durations:
            return []
        
        # Sort by duration
        trace_durations.sort(key=lambda x: x[1], reverse=True)
        
        # Get top percentile
        count = max(1, int(len(trace_durations) * (100 - percentile) / 100))
        return trace_durations[:count]
    
    def analyze_service_dependencies(self) -> Dict[str, Set[str]]:
        """Analyze service dependencies from traces"""
        dependencies = defaultdict(set)
        
        for trace_spans in self.traces.values():
            # Build span hierarchy
            span_map = {s.span_id: s for s in trace_spans}
            
            for span in trace_spans:
                if span.parent_span_id and span.parent_span_id in span_map:
                    parent_span = span_map[span.parent_span_id]
                    if parent_span.service_name != span.service_name:
                        dependencies[parent_span.service_name].add(span.service_name)
        
        return {service: list(deps) for service, deps in dependencies.items()}


# Global tracer instance
_global_tracer = DistributedTracer()


def get_tracer(service_name: str, exporter: SpanExporter = None) -> Tracer:
    """Get global tracer instance for service"""
    return _global_tracer.get_tracer(service_name, exporter)


def trace(operation_name: str, service_name: str = "unknown", 
          kind: SpanKind = SpanKind.INTERNAL,
          tags: Dict[str, Any] = None):
    """Decorator for tracing functions"""
    def decorator(func):
        tracer = get_tracer(service_name)
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                async with tracer.async_span(operation_name, kind=kind, tags=tags) as span:
                    span.set_tag("function.name", func.__name__)
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with tracer.span(operation_name, kind=kind, tags=tags) as span:
                    span.set_tag("function.name", func.__name__)
                    return func(*args, **kwargs)
            return sync_wrapper
    
    return decorator


# Usage examples
if __name__ == "__main__":
    import requests
    import asyncio
    import aiohttp
    
    logging.basicConfig(level=logging.INFO)
    
    # Setup memory exporter for testing
    memory_exporter = MemorySpanExporter()
    api_tracer = get_tracer("api-service", memory_exporter)
    db_tracer = get_tracer("database-service", memory_exporter)
    
    # Example 1: Manual span creation
    def example_database_operation():
        with db_tracer.span("query_users", kind=SpanKind.INTERNAL) as span:
            span.set_tag("db.statement", "SELECT * FROM users")
            span.set_tag("db.type", "postgresql")
            
            # Simulate database work
            time.sleep(0.1)
            
            span.add_event("query_executed", {"rows_returned": 42})
            return "users_data"
    
    def example_api_request():
        with api_tracer.span("handle_request", kind=SpanKind.SERVER) as span:
            span.set_tag("http.method", "GET")
            span.set_tag("http.url", "/api/users")
            
            # Call database
            with api_tracer.span("call_database", kind=SpanKind.CLIENT) as db_span:
                db_span.set_tag("service.name", "database-service")
                result = example_database_operation()
            
            span.set_tag("http.status_code", 200)
            return {"users": result}
    
    # Example 2: Using decorators
    @trace("process_user_data", service_name="user-service")
    def process_user_data(user_id: str):
        # Simulate processing
        time.sleep(0.05)
        return f"processed_{user_id}"
    
    @trace("async_api_call", service_name="external-service")
    async def async_api_call(url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()
    
    # Run examples
    async def run_examples():
        # Manual tracing
        result = example_api_request()
        print(f"API result: {result}")
        
        # Decorator tracing
        user_result = process_user_data("123")
        print(f"User processing result: {user_result}")
        
        # Async tracing
        try:
            api_result = await async_api_call("https://httpbin.org/delay/1")
            print(f"Async API call completed (length: {len(api_result)})")
        except Exception as e:
            print(f"Async API call failed: {e}")
        
        # Wait for spans to be processed
        time.sleep(2)
        
        # Analyze traces
        spans = memory_exporter.get_spans()
        analyzer = TraceAnalyzer(spans)
        
        stats = analyzer.get_trace_statistics()
        print(f"\nTrace Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        dependencies = analyzer.analyze_service_dependencies()
        print(f"\nService Dependencies:")
        for service, deps in dependencies.items():
            print(f"  {service} -> {deps}")
    
    # Run the examples
    asyncio.run(run_examples())
    
    # Cleanup
    _global_tracer.shutdown()