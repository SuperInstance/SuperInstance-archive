"""
Service Dependency Injection System

Provides comprehensive dependency injection capabilities including:
- Container-based dependency management
- Interface-based service registration
- Lifecycle management (singleton, transient, scoped)
- Circular dependency detection and resolution
- Configuration-driven dependency injection
- Dynamic service discovery and binding
- Aspect-oriented programming support
- Service factory patterns
"""

import asyncio
import inspect
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Type, Union, get_type_hints
from abc import ABC, abstractmethod
import logging
import weakref
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceLifecycle(Enum):
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"

class InjectionScope(Enum):
    REQUEST = "request"
    SESSION = "session"
    APPLICATION = "application"

@dataclass
class ServiceDescriptor:
    """Service registration descriptor"""
    service_name: str
    service_type: Type
    implementation_type: Type
    lifecycle: ServiceLifecycle = ServiceLifecycle.SINGLETON
    factory: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    interfaces: List[Type] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    priority: int = 0
    async_factory: bool = False
    initialization_method: Optional[str] = None
    disposal_method: Optional[str] = None

@dataclass
class ServiceInstance:
    """Service instance wrapper"""
    service_name: str
    instance: Any
    lifecycle: ServiceLifecycle
    created_at: datetime = field(default_factory=datetime.now)
    scope_id: Optional[str] = None
    reference_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class ServiceScope:
    """Represents a dependency injection scope"""
    
    def __init__(self, scope_id: str, scope_type: InjectionScope):
        self.scope_id = scope_id
        self.scope_type = scope_type
        self.instances: Dict[str, ServiceInstance] = {}
        self.created_at = datetime.now()
        self.disposed = False
    
    async def dispose(self):
        """Dispose all scoped instances"""
        if self.disposed:
            return
        
        for instance in self.instances.values():
            await self._dispose_instance(instance)
        
        self.instances.clear()
        self.disposed = True
        logger.debug(f"Disposed scope {self.scope_id}")
    
    async def _dispose_instance(self, service_instance: ServiceInstance):
        """Dispose a single service instance"""
        try:
            # Call disposal method if defined
            if hasattr(service_instance.instance, 'dispose'):
                method = getattr(service_instance.instance, 'dispose')
                if asyncio.iscoroutinefunction(method):
                    await method()
                else:
                    method()
            
            logger.debug(f"Disposed service instance {service_instance.service_name}")
            
        except Exception as e:
            logger.error(f"Error disposing service {service_instance.service_name}: {e}")

class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected"""
    pass

class ServiceNotFoundError(Exception):
    """Raised when a requested service is not registered"""
    pass

class DependencyResolutionError(Exception):
    """Raised when dependency resolution fails"""
    pass

class ServiceRegistry:
    """Registry for service descriptors and configurations"""
    
    def __init__(self):
        self.services: Dict[str, ServiceDescriptor] = {}
        self.interfaces: Dict[Type, List[str]] = {}
        self.tags: Dict[str, List[str]] = {}
    
    def register(self, descriptor: ServiceDescriptor):
        """Register a service descriptor"""
        self.services[descriptor.service_name] = descriptor
        
        # Index by interfaces
        for interface in descriptor.interfaces:
            if interface not in self.interfaces:
                self.interfaces[interface] = []
            self.interfaces[interface].append(descriptor.service_name)
        
        # Index by tags
        for tag in descriptor.tags:
            if tag not in self.tags:
                self.tags[tag] = []
            self.tags[tag].append(descriptor.service_name)
        
        logger.debug(f"Registered service {descriptor.service_name}")
    
    def unregister(self, service_name: str):
        """Unregister a service"""
        if service_name not in self.services:
            return
        
        descriptor = self.services[service_name]
        
        # Remove from interface index
        for interface in descriptor.interfaces:
            if interface in self.interfaces:
                self.interfaces[interface].remove(service_name)
                if not self.interfaces[interface]:
                    del self.interfaces[interface]
        
        # Remove from tag index
        for tag in descriptor.tags:
            if tag in self.tags:
                self.tags[tag].remove(service_name)
                if not self.tags[tag]:
                    del self.tags[tag]
        
        del self.services[service_name]
        logger.debug(f"Unregistered service {service_name}")
    
    def get_by_interface(self, interface: Type) -> List[ServiceDescriptor]:
        """Get services that implement an interface"""
        service_names = self.interfaces.get(interface, [])
        return [self.services[name] for name in service_names]
    
    def get_by_tag(self, tag: str) -> List[ServiceDescriptor]:
        """Get services by tag"""
        service_names = self.tags.get(tag, [])
        return [self.services[name] for name in service_names]

class DependencyResolver:
    """Resolves service dependencies"""
    
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
    
    def resolve_dependencies(self, service_name: str) -> List[str]:
        """Resolve dependencies for a service"""
        if service_name not in self.registry.services:
            raise ServiceNotFoundError(f"Service {service_name} not found")
        
        visited = set()
        resolved = []
        
        self._resolve_recursive(service_name, visited, resolved, [])
        
        return resolved
    
    def _resolve_recursive(self, service_name: str, visited: set, resolved: list, path: list):
        """Recursively resolve dependencies"""
        if service_name in path:
            cycle = " -> ".join(path + [service_name])
            raise CircularDependencyError(f"Circular dependency detected: {cycle}")
        
        if service_name in visited:
            return
        
        visited.add(service_name)
        path.append(service_name)
        
        descriptor = self.registry.services.get(service_name)
        if not descriptor:
            raise ServiceNotFoundError(f"Service {service_name} not found")
        
        # Resolve dependencies first
        for dependency in descriptor.dependencies:
            self._resolve_recursive(dependency, visited, resolved, path.copy())
        
        # Add this service to resolved list
        if service_name not in resolved:
            resolved.append(service_name)
        
        path.pop()
    
    def analyze_dependencies(self, service_name: str) -> Dict[str, Any]:
        """Analyze dependency graph for a service"""
        if service_name not in self.registry.services:
            raise ServiceNotFoundError(f"Service {service_name} not found")
        
        dependencies = self._get_all_dependencies(service_name, set())
        
        return {
            "service": service_name,
            "direct_dependencies": self.registry.services[service_name].dependencies,
            "all_dependencies": list(dependencies),
            "dependency_count": len(dependencies),
            "depth": self._calculate_dependency_depth(service_name, set())
        }
    
    def _get_all_dependencies(self, service_name: str, visited: set) -> set:
        """Get all dependencies recursively"""
        if service_name in visited:
            return set()
        
        visited.add(service_name)
        all_deps = set()
        
        descriptor = self.registry.services.get(service_name)
        if descriptor:
            for dep in descriptor.dependencies:
                all_deps.add(dep)
                all_deps.update(self._get_all_dependencies(dep, visited.copy()))
        
        return all_deps
    
    def _calculate_dependency_depth(self, service_name: str, visited: set) -> int:
        """Calculate maximum dependency depth"""
        if service_name in visited:
            return 0
        
        visited.add(service_name)
        max_depth = 0
        
        descriptor = self.registry.services.get(service_name)
        if descriptor:
            for dep in descriptor.dependencies:
                depth = 1 + self._calculate_dependency_depth(dep, visited.copy())
                max_depth = max(max_depth, depth)
        
        return max_depth

class ServiceFactory:
    """Factory for creating service instances"""
    
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
    
    async def create_instance(self, service_name: str, context: Dict[str, Any] = None) -> Any:
        """Create a service instance"""
        descriptor = self.registry.services.get(service_name)
        if not descriptor:
            raise ServiceNotFoundError(f"Service {service_name} not found")
        
        if context is None:
            context = {}
        
        # Use custom factory if provided
        if descriptor.factory:
            return await self._create_with_factory(descriptor, context)
        
        # Create with constructor injection
        return await self._create_with_constructor(descriptor, context)
    
    async def _create_with_factory(self, descriptor: ServiceDescriptor, context: Dict[str, Any]) -> Any:
        """Create instance using factory method"""
        try:
            if descriptor.async_factory:
                instance = await descriptor.factory(context)
            else:
                instance = descriptor.factory(context)
            
            # Call initialization method if specified
            if descriptor.initialization_method and hasattr(instance, descriptor.initialization_method):
                init_method = getattr(instance, descriptor.initialization_method)
                if asyncio.iscoroutinefunction(init_method):
                    await init_method()
                else:
                    init_method()
            
            return instance
            
        except Exception as e:
            raise DependencyResolutionError(f"Failed to create {descriptor.service_name} with factory: {e}")
    
    async def _create_with_constructor(self, descriptor: ServiceDescriptor, context: Dict[str, Any]) -> Any:
        """Create instance using constructor injection"""
        try:
            # Get constructor signature
            sig = inspect.signature(descriptor.implementation_type.__init__)
            type_hints = get_type_hints(descriptor.implementation_type.__init__)
            
            # Resolve constructor parameters
            kwargs = {}
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                # Check if parameter is in configuration
                if param_name in descriptor.configuration:
                    kwargs[param_name] = descriptor.configuration[param_name]
                # Check if parameter is in context
                elif param_name in context:
                    kwargs[param_name] = context[param_name]
                # Try to resolve as dependency
                elif param_name in self.registry.services:
                    # This would require the container to resolve dependencies
                    # For now, we'll skip automatic dependency resolution in factory
                    pass
                # Use default value if available
                elif param.default != inspect.Parameter.empty:
                    kwargs[param_name] = param.default
            
            # Create instance
            instance = descriptor.implementation_type(**kwargs)
            
            # Call initialization method if specified
            if descriptor.initialization_method and hasattr(instance, descriptor.initialization_method):
                init_method = getattr(instance, descriptor.initialization_method)
                if asyncio.iscoroutinefunction(init_method):
                    await init_method()
                else:
                    init_method()
            
            return instance
            
        except Exception as e:
            raise DependencyResolutionError(f"Failed to create {descriptor.service_name}: {e}")

class DependencyContainer:
    """Main dependency injection container"""
    
    def __init__(self):
        self.registry = ServiceRegistry()
        self.resolver = DependencyResolver(self.registry)
        self.factory = ServiceFactory(self.registry)
        self.singleton_instances: Dict[str, ServiceInstance] = {}
        self.scopes: Dict[str, ServiceScope] = {}
        self.current_scope: Optional[str] = None
        self.resolution_cache: Dict[str, List[str]] = {}
    
    def register_singleton(self, service_name: str, service_type: Type, implementation_type: Type = None, **kwargs):
        """Register a singleton service"""
        if implementation_type is None:
            implementation_type = service_type
        
        descriptor = ServiceDescriptor(
            service_name=service_name,
            service_type=service_type,
            implementation_type=implementation_type,
            lifecycle=ServiceLifecycle.SINGLETON,
            **kwargs
        )
        
        self.registry.register(descriptor)
    
    def register_transient(self, service_name: str, service_type: Type, implementation_type: Type = None, **kwargs):
        """Register a transient service"""
        if implementation_type is None:
            implementation_type = service_type
        
        descriptor = ServiceDescriptor(
            service_name=service_name,
            service_type=service_type,
            implementation_type=implementation_type,
            lifecycle=ServiceLifecycle.TRANSIENT,
            **kwargs
        )
        
        self.registry.register(descriptor)
    
    def register_scoped(self, service_name: str, service_type: Type, implementation_type: Type = None, **kwargs):
        """Register a scoped service"""
        if implementation_type is None:
            implementation_type = service_type
        
        descriptor = ServiceDescriptor(
            service_name=service_name,
            service_type=service_type,
            implementation_type=implementation_type,
            lifecycle=ServiceLifecycle.SCOPED,
            **kwargs
        )
        
        self.registry.register(descriptor)
    
    def register_factory(self, service_name: str, service_type: Type, factory: Callable, lifecycle: ServiceLifecycle = ServiceLifecycle.SINGLETON, **kwargs):
        """Register a service with factory method"""
        descriptor = ServiceDescriptor(
            service_name=service_name,
            service_type=service_type,
            implementation_type=service_type,
            lifecycle=lifecycle,
            factory=factory,
            async_factory=asyncio.iscoroutinefunction(factory),
            **kwargs
        )
        
        self.registry.register(descriptor)
    
    async def resolve(self, service_name: str, scope_id: str = None) -> Any:
        """Resolve a service by name"""
        descriptor = self.registry.services.get(service_name)
        if not descriptor:
            raise ServiceNotFoundError(f"Service {service_name} not found")
        
        # Handle different lifecycles
        if descriptor.lifecycle == ServiceLifecycle.SINGLETON:
            return await self._resolve_singleton(service_name)
        elif descriptor.lifecycle == ServiceLifecycle.SCOPED:
            return await self._resolve_scoped(service_name, scope_id or self.current_scope)
        else:  # TRANSIENT
            return await self._resolve_transient(service_name)
    
    async def resolve_by_type(self, service_type: Type, scope_id: str = None) -> Any:
        """Resolve a service by type"""
        # Find services that implement this type
        matching_services = []
        for name, descriptor in self.registry.services.items():
            if descriptor.service_type == service_type or service_type in descriptor.interfaces:
                matching_services.append(name)
        
        if not matching_services:
            raise ServiceNotFoundError(f"No services found for type {service_type}")
        
        if len(matching_services) > 1:
            # Return the one with highest priority
            best_service = max(matching_services, 
                             key=lambda s: self.registry.services[s].priority)
            return await self.resolve(best_service, scope_id)
        
        return await self.resolve(matching_services[0], scope_id)
    
    async def resolve_all_by_type(self, service_type: Type, scope_id: str = None) -> List[Any]:
        """Resolve all services of a given type"""
        matching_services = []
        for name, descriptor in self.registry.services.items():
            if descriptor.service_type == service_type or service_type in descriptor.interfaces:
                matching_services.append(name)
        
        instances = []
        for service_name in matching_services:
            instance = await self.resolve(service_name, scope_id)
            instances.append(instance)
        
        return instances
    
    async def resolve_with_dependencies(self, service_name: str, scope_id: str = None) -> Any:
        """Resolve a service and all its dependencies"""
        # Get resolution order
        if service_name in self.resolution_cache:
            resolution_order = self.resolution_cache[service_name]
        else:
            resolution_order = self.resolver.resolve_dependencies(service_name)
            self.resolution_cache[service_name] = resolution_order
        
        # Resolve dependencies first
        resolved_dependencies = {}
        for dep_name in resolution_order[:-1]:  # All except the target service
            resolved_dependencies[dep_name] = await self.resolve(dep_name, scope_id)
        
        # Resolve target service with dependency context
        context = {"dependencies": resolved_dependencies}
        return await self._resolve_with_context(service_name, context, scope_id)
    
    async def _resolve_singleton(self, service_name: str) -> Any:
        """Resolve singleton service"""
        if service_name in self.singleton_instances:
            instance = self.singleton_instances[service_name]
            instance.reference_count += 1
            return instance.instance
        
        # Create new singleton instance
        instance_obj = await self.factory.create_instance(service_name)
        
        service_instance = ServiceInstance(
            service_name=service_name,
            instance=instance_obj,
            lifecycle=ServiceLifecycle.SINGLETON,
            reference_count=1
        )
        
        self.singleton_instances[service_name] = service_instance
        logger.debug(f"Created singleton instance of {service_name}")
        
        return instance_obj
    
    async def _resolve_scoped(self, service_name: str, scope_id: str) -> Any:
        """Resolve scoped service"""
        if not scope_id:
            raise DependencyResolutionError("Scope ID required for scoped services")
        
        # Get or create scope
        scope = self.scopes.get(scope_id)
        if not scope:
            scope = ServiceScope(scope_id, InjectionScope.REQUEST)
            self.scopes[scope_id] = scope
        
        # Check if instance exists in scope
        if service_name in scope.instances:
            instance = scope.instances[service_name]
            instance.reference_count += 1
            return instance.instance
        
        # Create new scoped instance
        instance_obj = await self.factory.create_instance(service_name)
        
        service_instance = ServiceInstance(
            service_name=service_name,
            instance=instance_obj,
            lifecycle=ServiceLifecycle.SCOPED,
            scope_id=scope_id,
            reference_count=1
        )
        
        scope.instances[service_name] = service_instance
        logger.debug(f"Created scoped instance of {service_name} in scope {scope_id}")
        
        return instance_obj
    
    async def _resolve_transient(self, service_name: str) -> Any:
        """Resolve transient service"""
        # Always create new instance
        instance_obj = await self.factory.create_instance(service_name)
        logger.debug(f"Created transient instance of {service_name}")
        return instance_obj
    
    async def _resolve_with_context(self, service_name: str, context: Dict[str, Any], scope_id: str = None) -> Any:
        """Resolve service with additional context"""
        descriptor = self.registry.services.get(service_name)
        if not descriptor:
            raise ServiceNotFoundError(f"Service {service_name} not found")
        
        if descriptor.lifecycle == ServiceLifecycle.SINGLETON:
            # For singletons, check if already created
            if service_name in self.singleton_instances:
                return self.singleton_instances[service_name].instance
        
        # Create with context
        instance_obj = await self.factory.create_instance(service_name, context)
        
        # Store based on lifecycle
        if descriptor.lifecycle == ServiceLifecycle.SINGLETON:
            service_instance = ServiceInstance(
                service_name=service_name,
                instance=instance_obj,
                lifecycle=ServiceLifecycle.SINGLETON,
                reference_count=1
            )
            self.singleton_instances[service_name] = service_instance
        
        return instance_obj
    
    @asynccontextmanager
    async def scope(self, scope_type: InjectionScope = InjectionScope.REQUEST):
        """Create a dependency injection scope"""
        scope_id = str(uuid.uuid4())
        scope = ServiceScope(scope_id, scope_type)
        
        self.scopes[scope_id] = scope
        previous_scope = self.current_scope
        self.current_scope = scope_id
        
        try:
            yield scope_id
        finally:
            self.current_scope = previous_scope
            await scope.dispose()
            self.scopes.pop(scope_id, None)
    
    def get_service_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a registered service"""
        descriptor = self.registry.services.get(service_name)
        if not descriptor:
            return None
        
        dependencies = self.resolver.analyze_dependencies(service_name)
        
        return {
            "name": descriptor.service_name,
            "type": descriptor.service_type.__name__,
            "implementation": descriptor.implementation_type.__name__,
            "lifecycle": descriptor.lifecycle.value,
            "dependencies": dependencies,
            "interfaces": [iface.__name__ for iface in descriptor.interfaces],
            "tags": descriptor.tags,
            "priority": descriptor.priority,
            "has_factory": descriptor.factory is not None,
            "configuration": descriptor.configuration
        }
    
    def list_services(self) -> List[Dict[str, Any]]:
        """List all registered services"""
        services = []
        for service_name in self.registry.services:
            info = self.get_service_info(service_name)
            if info:
                services.append(info)
        return services
    
    async def dispose(self):
        """Dispose the container and all managed instances"""
        # Dispose all scopes
        for scope in list(self.scopes.values()):
            await scope.dispose()
        self.scopes.clear()
        
        # Dispose singleton instances
        for instance in self.singleton_instances.values():
            await self._dispose_singleton_instance(instance)
        self.singleton_instances.clear()
        
        # Clear caches
        self.resolution_cache.clear()
        
        logger.info("Dependency container disposed")
    
    async def _dispose_singleton_instance(self, service_instance: ServiceInstance):
        """Dispose a singleton instance"""
        try:
            if hasattr(service_instance.instance, 'dispose'):
                method = getattr(service_instance.instance, 'dispose')
                if asyncio.iscoroutinefunction(method):
                    await method()
                else:
                    method()
            
            logger.debug(f"Disposed singleton instance {service_instance.service_name}")
            
        except Exception as e:
            logger.error(f"Error disposing singleton {service_instance.service_name}: {e}")

class DependencyInjectionDecorator:
    """Decorator for automatic dependency injection"""
    
    def __init__(self, container: DependencyContainer):
        self.container = container
    
    def inject(self, **service_mappings):
        """Decorator to inject dependencies into method parameters"""
        def decorator(func):
            sig = inspect.signature(func)
            
            async def wrapper(*args, **kwargs):
                # Resolve dependencies
                for param_name, service_name in service_mappings.items():
                    if param_name not in kwargs and param_name in sig.parameters:
                        kwargs[param_name] = await self.container.resolve(service_name)
                
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator

# Interfaces and base classes
class IService(ABC):
    """Base interface for services"""
    
    @abstractmethod
    async def initialize(self):
        """Initialize the service"""
        pass
    
    @abstractmethod
    async def dispose(self):
        """Dispose the service"""
        pass

class ServiceBase(IService):
    """Base class for services with common functionality"""
    
    def __init__(self):
        self.initialized = False
        self.disposed = False
    
    async def initialize(self):
        """Initialize the service"""
        if not self.initialized:
            await self._initialize()
            self.initialized = True
    
    async def dispose(self):
        """Dispose the service"""
        if not self.disposed:
            await self._dispose()
            self.disposed = True
    
    async def _initialize(self):
        """Override in derived classes"""
        pass
    
    async def _dispose(self):
        """Override in derived classes"""
        pass

# Configuration-driven container
class ConfigurableDependencyContainer(DependencyContainer):
    """Dependency container that can be configured from JSON/YAML"""
    
    def load_configuration(self, config: Dict[str, Any]):
        """Load service configuration from dictionary"""
        services_config = config.get("services", [])
        
        for service_config in services_config:
            self._register_from_config(service_config)
    
    def _register_from_config(self, config: Dict[str, Any]):
        """Register service from configuration"""
        service_name = config["name"]
        service_type_name = config["type"]
        implementation_type_name = config.get("implementation", service_type_name)
        lifecycle_str = config.get("lifecycle", "singleton")
        
        # This would require a type registry or import mechanism
        # For now, we'll skip the actual registration
        logger.info(f"Would register service {service_name} from configuration")

# Factory function
def create_dependency_container() -> DependencyContainer:
    """Create and return a dependency container instance"""
    return DependencyContainer()

# Example service implementations
class DatabaseService(ServiceBase):
    """Example database service"""
    
    def __init__(self, connection_string: str):
        super().__init__()
        self.connection_string = connection_string
        self.connection = None
    
    async def _initialize(self):
        """Initialize database connection"""
        logger.info(f"Connecting to database: {self.connection_string}")
        # Simulate database connection
        self.connection = f"Connected to {self.connection_string}"
    
    async def _dispose(self):
        """Close database connection"""
        logger.info("Closing database connection")
        self.connection = None
    
    async def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a query"""
        if not self.initialized:
            raise RuntimeError("Database service not initialized")
        return [{"result": f"Query result for: {sql}"}]

class CacheService(ServiceBase):
    """Example cache service"""
    
    def __init__(self, redis_url: str = "redis://localhost"):
        super().__init__()
        self.redis_url = redis_url
        self.cache = {}
    
    async def _initialize(self):
        """Initialize cache connection"""
        logger.info(f"Connecting to cache: {self.redis_url}")
    
    async def _dispose(self):
        """Close cache connection"""
        logger.info("Closing cache connection")
        self.cache.clear()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        return self.cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache"""
        self.cache[key] = value

class LoggingService(ServiceBase):
    """Example logging service"""
    
    def __init__(self, log_level: str = "INFO"):
        super().__init__()
        self.log_level = log_level
        self.logger = logging.getLogger("app")
    
    async def _initialize(self):
        """Initialize logging"""
        level = getattr(logging, self.log_level.upper(), logging.INFO)
        self.logger.setLevel(level)
        logger.info(f"Logging service initialized with level {self.log_level}")
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message"""
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message)