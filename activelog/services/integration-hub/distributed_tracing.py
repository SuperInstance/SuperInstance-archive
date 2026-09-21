"""
ActiveLog Integration Hub - Distributed Tracing
Complete distributed tracing system for tracking requests across all 70+ services
"""

import asyncio
import time
import json
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
import aiohttp
from contextlib import asynccontextmanager
import threading
from collections import defaultdict
import statistics

class SpanKind(Enum):
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"

class SpanStatus(Enum):
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

@dataclass
class SpanAttribute:
    key: str
    value: Any
    type: str = "string"  # string, int, float, bool, array

@dataclass
class SpanEvent:
    name: str
    timestamp: datetime
    attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SpanLink:
    trace_id: str
    span_id: str
    attributes: Dict[str, Any] = field(default_factory=dict)

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
    status: SpanStatus = SpanStatus.OK
    span_kind: SpanKind = SpanKind.INTERNAL
    attributes: Dict[str, SpanAttribute] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanLink] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.span_id:
            self.span_id = self.generate_span_id()
    
    @staticmethod
    def generate_span_id() -> str:
        """Generate unique span ID"""
        return f"{int(time.time() * 1000000) % 2**63:016x}"
    
    def finish(self, status: SpanStatus = SpanStatus.OK):
        """Finish the span"""
        self.end_time = datetime.now()
        self.status = status
        if self.start_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
    
    def set_attribute(self, key: str, value: Any):
        """Set span attribute"""
        attr_type = type(value).__name__
        self.attributes[key] = SpanAttribute(key=key, value=value, type=attr_type)
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add event to span"""
        self.events.append(SpanEvent(
            name=name,
            timestamp=datetime.now(),
            attributes=attributes or {}
        ))
    
    def add_link(self, trace_id: str, span_id: str, attributes: Optional[Dict[str, Any]] = None):
        """Add link to another span"""
        self.links.append(SpanLink(
            trace_id=trace_id,
            span_id=span_id,
            attributes=attributes or {}
        ))
    
    def set_tag(self, key: str, value: str):
        """Set span tag (legacy Jaeger style)"""
        self.tags[key] = value
    
    def log(self, fields: Dict[str, Any]):
        """Add log entry (legacy Jaeger style)"""
        self.logs.append({
            'timestamp': datetime.now().isoformat(),
            'fields': fields
        })

@dataclass
class Trace:
    trace_id: str
    spans: List[Span] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    service_count: int = 0
    span_count: int = 0
    error_count: int = 0
    root_service: str = ""
    root_operation: str = ""
    
    def add_span(self, span: Span):
        """Add span to trace"""
        self.spans.append(span)
        self.span_count = len(self.spans)
        
        # Update trace metadata
        if not self.start_time or span.start_time < self.start_time:
            self.start_time = span.start_time
        
        if span.end_time and (not self.end_time or span.end_time > self.end_time):
            self.end_time = span.end_time
        
        if self.start_time and self.end_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        
        # Count services and errors
        services = set(s.service_name for s in self.spans)
        self.service_count = len(services)
        self.error_count = sum(1 for s in self.spans if s.status == SpanStatus.ERROR)
        
        # Set root service and operation (span without parent)
        root_spans = [s for s in self.spans if not s.parent_span_id]
        if root_spans:
            root_span = min(root_spans, key=lambda s: s.start_time)
            self.root_service = root_span.service_name
            self.root_operation = root_span.operation_name

class SpanContext:
    """Context for current span in a thread/task"""
    def __init__(self, span: Span):
        self.span = span
        self.trace_id = span.trace_id
        self.span_id = span.span_id
        self.baggage: Dict[str, str] = {}

class TracingContext:
    """Thread-local tracing context"""
    def __init__(self):
        self._local = threading.local()
    
    @property
    def current_span(self) -> Optional[Span]:
        """Get current active span"""
        return getattr(self._local, 'current_span', None)
    
    @current_span.setter
    def current_span(self, span: Optional[Span]):
        """Set current active span"""
        self._local.current_span = span
    
    @property
    def current_trace_id(self) -> Optional[str]:
        """Get current trace ID"""
        if self.current_span:
            return self.current_span.trace_id
        return None

class TracingCollector:
    """Collects and batches spans for export"""
    def __init__(self, batch_size: int = 100, flush_interval: int = 5):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.spans_buffer: List[Span] = []
        self.exporters: List['SpanExporter'] = []
        self.running = False
        
    def add_exporter(self, exporter: 'SpanExporter'):
        """Add span exporter"""
        self.exporters.append(exporter)
    
    def collect_span(self, span: Span):
        """Collect span for batching"""
        self.spans_buffer.append(span)
        
        if len(self.spans_buffer) >= self.batch_size:
            asyncio.create_task(self.flush_spans())
    
    async def flush_spans(self):
        """Flush collected spans to exporters"""
        if not self.spans_buffer:
            return
        
        spans_to_export = self.spans_buffer[:]
        self.spans_buffer.clear()
        
        for exporter in self.exporters:
            try:
                await exporter.export_spans(spans_to_export)
            except Exception as e:
                logging.error(f"Failed to export spans: {e}")
    
    async def start_background_flush(self):
        """Start background flushing task"""
        self.running = True
        while self.running:
            await asyncio.sleep(self.flush_interval)
            await self.flush_spans()
    
    def stop(self):
        """Stop collector"""
        self.running = False

class SpanExporter:
    """Base class for span exporters"""
    async def export_spans(self, spans: List[Span]):
        """Export spans to backend"""
        raise NotImplementedError

class ConsoleSpanExporter(SpanExporter):
    """Export spans to console"""
    async def export_spans(self, spans: List[Span]):
        for span in spans:
            print(f"TRACE [{span.trace_id[:8]}] {span.service_name}::{span.operation_name} "
                  f"({span.duration_ms:.1f}ms) - {span.status.value}")

class FileSpanExporter(SpanExporter):
    """Export spans to file"""
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def export_spans(self, spans: List[Span]):
        with open(self.file_path, 'a') as f:
            for span in spans:
                span_data = {
                    'timestamp': span.start_time.isoformat(),
                    'trace_id': span.trace_id,
                    'span_id': span.span_id,
                    'parent_span_id': span.parent_span_id,
                    'service_name': span.service_name,
                    'operation_name': span.operation_name,
                    'duration_ms': span.duration_ms,
                    'status': span.status.value,
                    'attributes': {k: v.value for k, v in span.attributes.items()},
                    'events': [asdict(event) for event in span.events],
                    'tags': span.tags
                }
                f.write(json.dumps(span_data) + '\n')

class JaegerSpanExporter(SpanExporter):
    """Export spans to Jaeger"""
    def __init__(self, jaeger_endpoint: str = "http://localhost:14268/api/traces"):
        self.endpoint = jaeger_endpoint
        self.session = aiohttp.ClientSession()
    
    async def export_spans(self, spans: List[Span]):
        # Convert spans to Jaeger format
        jaeger_spans = []
        
        for span in spans:
            jaeger_span = {
                'traceID': span.trace_id,
                'spanID': span.span_id,
                'parentSpanID': span.parent_span_id,
                'operationName': span.operation_name,
                'startTime': int(span.start_time.timestamp() * 1000000),  # microseconds
                'duration': int(span.duration_ms * 1000) if span.duration_ms else 0,
                'tags': [
                    {'key': 'service.name', 'value': span.service_name, 'type': 'string'},
                    {'key': 'span.kind', 'value': span.span_kind.value, 'type': 'string'}
                ],
                'logs': [],
                'process': {
                    'serviceName': span.service_name,
                    'tags': [
                        {'key': 'hostname', 'value': 'activelog-integration-hub', 'type': 'string'}
                    ]
                }
            }
            
            # Add attributes as tags
            for attr in span.attributes.values():
                jaeger_span['tags'].append({
                    'key': attr.key,
                    'value': str(attr.value),
                    'type': attr.type
                })
            
            # Add events as logs
            for event in span.events:
                jaeger_span['logs'].append({
                    'timestamp': int(event.timestamp.timestamp() * 1000000),
                    'fields': [
                        {'key': 'event', 'value': event.name},
                        *[{'key': k, 'value': str(v)} for k, v in event.attributes.items()]
                    ]
                })
            
            jaeger_spans.append(jaeger_span)
        
        # Group spans by trace
        traces_by_id = defaultdict(list)
        for span in jaeger_spans:
            traces_by_id[span['traceID']].append(span)
        
        # Send to Jaeger
        for trace_id, trace_spans in traces_by_id.items():
            jaeger_trace = {
                'traceID': trace_id,
                'spans': trace_spans
            }
            
            try:
                async with self.session.post(
                    self.endpoint,
                    json={'data': [jaeger_trace]},
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status != 200:
                        logging.warning(f"Failed to export trace {trace_id}: {response.status}")
            except Exception as e:
                logging.error(f"Failed to send trace to Jaeger: {e}")

class DistributedTracer:
    """Main distributed tracing system"""
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.context = TracingContext()
        self.collector = TracingCollector()
        self.traces: Dict[str, Trace] = {}
        self.sampling_rate = 1.0  # 100% sampling by default
        
        # Setup exporters
        self.setup_exporters()
        
        # Start collector
        asyncio.create_task(self.collector.start_background_flush())
    
    def setup_exporters(self):
        """Setup default exporters"""
        # Console exporter for debugging
        self.collector.add_exporter(ConsoleSpanExporter())
        
        # File exporter for persistence
        traces_dir = Path("/home/activeloguser/activelog/traces")
        traces_dir.mkdir(exist_ok=True)
        self.collector.add_exporter(FileSpanExporter(traces_dir / "spans.jsonl"))
        
        # Jaeger exporter (if available)
        try:
            self.collector.add_exporter(JaegerSpanExporter())
        except Exception:
            logging.warning("Jaeger exporter not available")
    
    def should_sample(self) -> bool:
        """Determine if trace should be sampled"""
        import random
        return random.random() < self.sampling_rate
    
    def generate_trace_id(self) -> str:
        """Generate unique trace ID"""
        return f"{int(time.time() * 1000000) % 2**63:016x}{uuid.uuid4().hex[:16]}"
    
    def start_span(self, operation_name: str, 
                   parent_context: Optional[SpanContext] = None,
                   span_kind: SpanKind = SpanKind.INTERNAL,
                   tags: Optional[Dict[str, str]] = None) -> Span:
        """Start a new span"""
        
        # Determine trace ID and parent
        if parent_context:
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
        elif self.context.current_span:
            trace_id = self.context.current_span.trace_id
            parent_span_id = self.context.current_span.span_id
        else:
            # Root span
            trace_id = self.generate_trace_id()
            parent_span_id = None
            
            # Apply sampling decision
            if not self.should_sample():
                # Return no-op span
                return NoOpSpan()
        
        # Create span
        span = Span(
            trace_id=trace_id,
            span_id=Span.generate_span_id(),
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=self.service_name,
            start_time=datetime.now(),
            span_kind=span_kind
        )
        
        # Add tags
        if tags:
            span.tags.update(tags)
        
        # Add to trace
        if trace_id not in self.traces:
            self.traces[trace_id] = Trace(trace_id=trace_id)
        
        self.traces[trace_id].add_span(span)
        
        return span
    
    def finish_span(self, span: Span):
        """Finish a span"""
        if isinstance(span, NoOpSpan):
            return
        
        span.finish()
        
        # Collect span for export
        self.collector.collect_span(span)
    
    @asynccontextmanager
    async def trace(self, operation_name: str, 
                    span_kind: SpanKind = SpanKind.INTERNAL,
                    tags: Optional[Dict[str, str]] = None):
        """Context manager for tracing"""
        span = self.start_span(operation_name, span_kind=span_kind, tags=tags)
        
        # Set as current span
        previous_span = self.context.current_span
        self.context.current_span = span
        
        try:
            yield span
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            span.add_event("exception", {"message": str(e), "type": type(e).__name__})
            span.status = SpanStatus.ERROR
            raise
        finally:
            self.finish_span(span)
            self.context.current_span = previous_span
    
    def trace_function(self, operation_name: Optional[str] = None,
                      span_kind: SpanKind = SpanKind.INTERNAL,
                      tags: Optional[Dict[str, str]] = None):
        """Decorator for tracing functions"""
        def decorator(func):
            nonlocal operation_name
            if operation_name is None:
                operation_name = f"{func.__module__}.{func.__name__}"
            
            if asyncio.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    async with self.trace(operation_name, span_kind, tags) as span:
                        # Add function arguments as attributes
                        if args:
                            span.set_attribute("function.args", str(args))
                        if kwargs:
                            span.set_attribute("function.kwargs", str(kwargs))
                        
                        result = await func(*args, **kwargs)
                        
                        # Add result info
                        if result is not None:
                            span.set_attribute("function.result_type", type(result).__name__)
                        
                        return result
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    span = self.start_span(operation_name, span_kind=span_kind, tags=tags)
                    previous_span = self.context.current_span
                    self.context.current_span = span
                    
                    try:
                        # Add function arguments as attributes
                        if args:
                            span.set_attribute("function.args", str(args))
                        if kwargs:
                            span.set_attribute("function.kwargs", str(kwargs))
                        
                        result = func(*args, **kwargs)
                        
                        # Add result info
                        if result is not None:
                            span.set_attribute("function.result_type", type(result).__name__)
                        
                        return result
                    except Exception as e:
                        span.set_attribute("error", True)
                        span.set_attribute("error.message", str(e))
                        span.add_event("exception", {"message": str(e), "type": type(e).__name__})
                        span.status = SpanStatus.ERROR
                        raise
                    finally:
                        self.finish_span(span)
                        self.context.current_span = previous_span
                
                return sync_wrapper
        return decorator
    
    def inject_context(self, span_context: SpanContext, carrier: Dict[str, str]):
        """Inject span context into carrier (e.g., HTTP headers)"""
        carrier['X-Trace-ID'] = span_context.trace_id
        carrier['X-Span-ID'] = span_context.span_id
        
        # Add baggage
        for key, value in span_context.baggage.items():
            carrier[f'X-Baggage-{key}'] = value
    
    def extract_context(self, carrier: Dict[str, str]) -> Optional[SpanContext]:
        """Extract span context from carrier (e.g., HTTP headers)"""
        trace_id = carrier.get('X-Trace-ID')
        span_id = carrier.get('X-Span-ID')
        
        if not trace_id or not span_id:
            return None
        
        # Create dummy span for context
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=None,
            operation_name="extracted",
            service_name="unknown",
            start_time=datetime.now()
        )
        
        context = SpanContext(span)
        
        # Extract baggage
        for key, value in carrier.items():
            if key.startswith('X-Baggage-'):
                baggage_key = key[10:]  # Remove 'X-Baggage-' prefix
                context.baggage[baggage_key] = value
        
        return context
    
    def get_trace_analysis(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Analyze a specific trace"""
        if trace_id not in self.traces:
            return None
        
        trace = self.traces[trace_id]
        spans = trace.spans
        
        if not spans:
            return None
        
        # Build span tree
        span_tree = self.build_span_tree(spans)
        
        # Calculate statistics
        response_times = [s.duration_ms for s in spans if s.duration_ms]
        
        analysis = {
            'trace_id': trace_id,
            'total_spans': len(spans),
            'total_duration_ms': trace.duration_ms,
            'service_count': trace.service_count,
            'error_count': trace.error_count,
            'root_service': trace.root_service,
            'root_operation': trace.root_operation,
            'services_involved': list(set(s.service_name for s in spans)),
            'span_tree': span_tree,
            'critical_path': self.find_critical_path(spans),
            'bottlenecks': self.find_bottlenecks(spans),
            'statistics': {
                'avg_span_duration_ms': statistics.mean(response_times) if response_times else 0,
                'max_span_duration_ms': max(response_times) if response_times else 0,
                'min_span_duration_ms': min(response_times) if response_times else 0,
                'total_network_calls': len([s for s in spans if s.span_kind == SpanKind.CLIENT]),
                'database_calls': len([s for s in spans if 'db' in s.operation_name.lower()]),
                'external_calls': len([s for s in spans if 'http' in s.operation_name.lower()])
            }
        }
        
        return analysis
    
    def build_span_tree(self, spans: List[Span]) -> Dict[str, Any]:
        """Build hierarchical span tree"""
        span_map = {span.span_id: span for span in spans}
        root_spans = [span for span in spans if not span.parent_span_id]
        
        def build_tree_node(span: Span) -> Dict[str, Any]:
            children = [s for s in spans if s.parent_span_id == span.span_id]
            
            node = {
                'span_id': span.span_id,
                'operation_name': span.operation_name,
                'service_name': span.service_name,
                'duration_ms': span.duration_ms,
                'status': span.status.value,
                'start_time': span.start_time.isoformat(),
                'children': [build_tree_node(child) for child in children]
            }
            
            return node
        
        if root_spans:
            root_span = min(root_spans, key=lambda s: s.start_time)
            return build_tree_node(root_span)
        
        return {}
    
    def find_critical_path(self, spans: List[Span]) -> List[Dict[str, Any]]:
        """Find the critical path (longest duration chain)"""
        span_map = {span.span_id: span for span in spans}
        
        # Find root spans
        root_spans = [span for span in spans if not span.parent_span_id]
        if not root_spans:
            return []
        
        root_span = min(root_spans, key=lambda s: s.start_time)
        
        def find_longest_path(span: Span, current_path: List[Span]) -> List[Span]:
            current_path = current_path + [span]
            children = [s for s in spans if s.parent_span_id == span.span_id]
            
            if not children:
                return current_path
            
            # Find child with longest duration
            longest_child = max(children, key=lambda s: s.duration_ms or 0)
            return find_longest_path(longest_child, current_path)
        
        critical_path_spans = find_longest_path(root_span, [])
        
        return [
            {
                'span_id': span.span_id,
                'operation_name': span.operation_name,
                'service_name': span.service_name,
                'duration_ms': span.duration_ms
            }
            for span in critical_path_spans
        ]
    
    def find_bottlenecks(self, spans: List[Span]) -> List[Dict[str, Any]]:
        """Find performance bottlenecks"""
        if not spans:
            return []
        
        # Sort spans by duration
        sorted_spans = sorted(spans, key=lambda s: s.duration_ms or 0, reverse=True)
        
        # Take top 20% as potential bottlenecks
        bottleneck_count = max(1, len(sorted_spans) // 5)
        bottlenecks = sorted_spans[:bottleneck_count]
        
        return [
            {
                'span_id': span.span_id,
                'operation_name': span.operation_name,
                'service_name': span.service_name,
                'duration_ms': span.duration_ms,
                'percentage_of_trace': (span.duration_ms / max(s.duration_ms or 0 for s in spans)) * 100 if spans else 0
            }
            for span in bottlenecks
            if span.duration_ms and span.duration_ms > 0
        ]
    
    def get_service_map(self) -> Dict[str, Any]:
        """Generate service dependency map from traces"""
        service_connections = defaultdict(set)
        service_stats = defaultdict(lambda: {'call_count': 0, 'error_count': 0, 'avg_duration': 0})
        
        for trace in self.traces.values():
            for span in trace.spans:
                service_name = span.service_name
                service_stats[service_name]['call_count'] += 1
                
                if span.status == SpanStatus.ERROR:
                    service_stats[service_name]['error_count'] += 1
                
                if span.duration_ms:
                    current_avg = service_stats[service_name]['avg_duration']
                    call_count = service_stats[service_name]['call_count']
                    service_stats[service_name]['avg_duration'] = (
                        (current_avg * (call_count - 1) + span.duration_ms) / call_count
                    )
                
                # Find downstream services
                children = [s for s in trace.spans if s.parent_span_id == span.span_id]
                for child in children:
                    if child.service_name != service_name:
                        service_connections[service_name].add(child.service_name)
        
        # Convert to serializable format
        service_map = {
            'services': {
                service: {
                    'call_count': stats['call_count'],
                    'error_count': stats['error_count'],
                    'error_rate': (stats['error_count'] / stats['call_count']) * 100 if stats['call_count'] > 0 else 0,
                    'avg_duration_ms': stats['avg_duration'],
                    'downstream_services': list(service_connections[service])
                }
                for service, stats in service_stats.items()
            },
            'total_services': len(service_stats),
            'total_connections': sum(len(connections) for connections in service_connections.values())
        }
        
        return service_map
    
    def cleanup_old_traces(self, max_age_hours: int = 24):
        """Clean up old traces to prevent memory leaks"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        traces_to_remove = []
        for trace_id, trace in self.traces.items():
            if trace.start_time and trace.start_time < cutoff_time:
                traces_to_remove.append(trace_id)
        
        for trace_id in traces_to_remove:
            del self.traces[trace_id]
        
        logging.info(f"Cleaned up {len(traces_to_remove)} old traces")

class NoOpSpan(Span):
    """No-op span for when sampling is disabled"""
    def __init__(self):
        pass
    
    def finish(self, status: SpanStatus = SpanStatus.OK):
        pass
    
    def set_attribute(self, key: str, value: Any):
        pass
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        pass
    
    def set_tag(self, key: str, value: str):
        pass
    
    def log(self, fields: Dict[str, Any]):
        pass

# HTTP integration helpers
class TracingHTTPClientSession:
    """HTTP client with automatic tracing"""
    def __init__(self, tracer: DistributedTracer):
        self.tracer = tracer
        self.session = aiohttp.ClientSession()
    
    async def request(self, method: str, url: str, **kwargs):
        """Make HTTP request with tracing"""
        async with self.tracer.trace(
            operation_name=f"HTTP {method} {url}",
            span_kind=SpanKind.CLIENT,
            tags={'http.method': method, 'http.url': url}
        ) as span:
            
            # Inject trace context into headers
            headers = kwargs.get('headers', {})
            if self.tracer.context.current_span:
                context = SpanContext(self.tracer.context.current_span)
                self.tracer.inject_context(context, headers)
            
            kwargs['headers'] = headers
            
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    span.set_attribute('http.status_code', response.status)
                    span.set_attribute('http.response_size', len(await response.read()))
                    
                    if response.status >= 400:
                        span.status = SpanStatus.ERROR
                        span.set_attribute('error', True)
                    
                    return response
                    
            except Exception as e:
                span.status = SpanStatus.ERROR
                span.set_attribute('error', True)
                span.set_attribute('error.message', str(e))
                raise
    
    async def close(self):
        await self.session.close()

# Global tracer instance
_global_tracer: Optional[DistributedTracer] = None

def init_tracing(service_name: str) -> DistributedTracer:
    """Initialize global tracer"""
    global _global_tracer
    _global_tracer = DistributedTracer(service_name)
    return _global_tracer

def get_tracer() -> Optional[DistributedTracer]:
    """Get global tracer"""
    return _global_tracer

# Convenience functions
def trace(operation_name: str, **kwargs):
    """Trace decorator using global tracer"""
    if _global_tracer:
        return _global_tracer.trace_function(operation_name, **kwargs)
    
    def no_op_decorator(func):
        return func
    return no_op_decorator

async def start_trace_context(operation_name: str, **kwargs):
    """Start trace context using global tracer"""
    if _global_tracer:
        return _global_tracer.trace(operation_name, **kwargs)
    
    # No-op context manager
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def no_op_context():
        yield NoOpSpan()
    
    return no_op_context()

# Example usage
async def main():
    # Initialize tracing
    tracer = init_tracing("integration-hub")
    
    # Example traced function
    @tracer.trace_function("example_operation")
    async def example_operation():
        await asyncio.sleep(0.1)
        
        # Nested operation
        async with tracer.trace("nested_operation") as span:
            span.set_attribute("user_id", "12345")
            span.add_event("processing_started")
            await asyncio.sleep(0.05)
            span.add_event("processing_completed")
        
        return "success"
    
    # Run example
    result = await example_operation()
    print(f"Result: {result}")
    
    # Wait for spans to be exported
    await asyncio.sleep(1)
    
    # Get trace analysis
    if tracer.traces:
        trace_id = list(tracer.traces.keys())[0]
        analysis = tracer.get_trace_analysis(trace_id)
        print(f"Trace analysis: {json.dumps(analysis, indent=2, default=str)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())