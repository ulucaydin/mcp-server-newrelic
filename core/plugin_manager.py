"""
Enhanced plugin management system with dependency resolution
"""

import importlib
import inspect
import logging
import threading
from typing import Dict, List, Set, Optional, Any, Type, Callable
from dataclasses import dataclass, field
from pathlib import Path
import os
import sys
from collections import defaultdict
import graphlib
import yaml
import json

from fastmcp import FastMCP
from .plugin_loader import PluginBase

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """Metadata for a plugin"""
    name: str
    version: str
    description: str
    author: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    required_services: List[str] = field(default_factory=list)
    provides_services: List[str] = field(default_factory=list)
    config_schema: Optional[Dict[str, Any]] = None
    enabled: bool = True
    priority: int = 100  # Lower number = higher priority
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginMetadata':
        """Create from dictionary"""
        return cls(**data)
    
    @classmethod
    def from_plugin_class(cls, plugin_cls: Type[PluginBase]) -> 'PluginMetadata':
        """Extract metadata from plugin class"""
        # Check for metadata attribute
        if hasattr(plugin_cls, 'metadata'):
            if isinstance(plugin_cls.metadata, dict):
                return cls.from_dict(plugin_cls.metadata)
            elif isinstance(plugin_cls.metadata, PluginMetadata):
                return plugin_cls.metadata
        
        # Extract from docstring and attributes
        return cls(
            name=getattr(plugin_cls, 'name', plugin_cls.__name__),
            version=getattr(plugin_cls, 'version', '1.0.0'),
            description=getattr(plugin_cls, 'description', 
                              plugin_cls.__doc__ or 'No description'),
            author=getattr(plugin_cls, 'author', None),
            dependencies=getattr(plugin_cls, 'dependencies', []),
            required_services=getattr(plugin_cls, 'required_services', []),
            provides_services=getattr(plugin_cls, 'provides_services', []),
            config_schema=getattr(plugin_cls, 'config_schema', None),
            enabled=getattr(plugin_cls, 'enabled', True),
            priority=getattr(plugin_cls, 'priority', 100)
        )


@dataclass
class PluginInstance:
    """Represents a loaded plugin instance"""
    plugin_class: Type[PluginBase]
    metadata: PluginMetadata
    config: Dict[str, Any] = field(default_factory=dict)
    state: str = "unloaded"  # unloaded, loading, loaded, failed
    error: Optional[str] = None
    provided_tools: List[str] = field(default_factory=list)
    provided_resources: List[str] = field(default_factory=list)
    
    @property
    def is_loaded(self) -> bool:
        return self.state == "loaded"


class PluginDependencyResolver:
    """Resolves plugin dependencies"""
    
    def __init__(self):
        self.graph = graphlib.TopologicalSorter()
        self.plugins: Dict[str, PluginInstance] = {}
    
    def add_plugin(self, plugin: PluginInstance):
        """Add plugin to dependency graph"""
        self.plugins[plugin.metadata.name] = plugin
        
        # Add to graph with dependencies
        deps = plugin.metadata.dependencies
        if deps:
            self.graph.add(plugin.metadata.name, *deps)
        else:
            self.graph.add(plugin.metadata.name)
    
    def resolve(self) -> List[PluginInstance]:
        """Resolve dependencies and return load order"""
        try:
            # Prepare the graph
            self.graph.prepare()
            
            # Get ordered list
            load_order = []
            while self.graph.is_active():
                ready = self.graph.get_ready()
                
                # Sort by priority within same dependency level
                ready_plugins = [self.plugins[name] for name in ready 
                               if name in self.plugins]
                ready_plugins.sort(key=lambda p: p.metadata.priority)
                
                load_order.extend(ready_plugins)
                
                # Mark as done
                for plugin in ready_plugins:
                    self.graph.done(plugin.metadata.name)
            
            return load_order
            
        except graphlib.CycleError as e:
            raise ValueError(f"Circular dependency detected: {e}")
    
    def check_missing_dependencies(self) -> Dict[str, List[str]]:
        """Check for missing dependencies"""
        missing = defaultdict(list)
        
        for name, plugin in self.plugins.items():
            for dep in plugin.metadata.dependencies:
                if dep not in self.plugins:
                    missing[name].append(dep)
        
        return dict(missing)


class PluginConfigManager:
    """Manages plugin configuration"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or "configs/plugins")
        self.configs: Dict[str, Dict[str, Any]] = {}
        self._load_configs()
    
    def _load_configs(self):
        """Load plugin configurations from files"""
        if not self.config_dir.exists():
            return
        
        # Load YAML and JSON config files
        for config_file in self.config_dir.glob("*.{yaml,yml,json}"):
            try:
                with open(config_file, 'r') as f:
                    if config_file.suffix in ['.yaml', '.yml']:
                        config = yaml.safe_load(f)
                    else:
                        config = json.load(f)
                
                plugin_name = config_file.stem
                self.configs[plugin_name] = config
                
            except Exception as e:
                logger.error(f"Failed to load config {config_file}: {e}")
    
    def get_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get configuration for a plugin"""
        # Check for environment variable overrides
        env_prefix = f"PLUGIN_{plugin_name.upper()}_"
        env_config = {}
        
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                config_key = key[len(env_prefix):].lower()
                env_config[config_key] = value
        
        # Merge file config with env config
        file_config = self.configs.get(plugin_name, {})
        return {**file_config, **env_config}
    
    def validate_config(self, config: Dict[str, Any], 
                       schema: Optional[Dict[str, Any]]) -> bool:
        """Validate configuration against schema"""
        if not schema:
            return True
        
        # Simple validation - check required fields
        required = schema.get('required', [])
        for field in required:
            if field not in config:
                logger.error(f"Missing required config field: {field}")
                return False
        
        # Check types
        properties = schema.get('properties', {})
        for field, value in config.items():
            if field in properties:
                expected_type = properties[field].get('type')
                if expected_type:
                    # Simple type checking
                    type_map = {
                        'string': str,
                        'integer': int,
                        'number': (int, float),
                        'boolean': bool,
                        'array': list,
                        'object': dict
                    }
                    expected = type_map.get(expected_type)
                    if expected and not isinstance(value, expected):
                        logger.error(
                            f"Config field {field} has wrong type. "
                            f"Expected {expected_type}, got {type(value).__name__}"
                        )
                        return False
        
        return True


class ServiceRegistry:
    """Registry for services provided by plugins"""
    
    def __init__(self):
        self.services: Dict[str, Any] = {}
        self.providers: Dict[str, str] = {}  # service -> plugin name
    
    def register(self, service_name: str, service: Any, provider: str):
        """Register a service"""
        if service_name in self.services:
            logger.warning(
                f"Service {service_name} already registered by {self.providers[service_name]}. "
                f"Overriding with {provider}"
            )
        
        self.services[service_name] = service
        self.providers[service_name] = provider
        logger.debug(f"Registered service {service_name} from {provider}")
    
    def get(self, service_name: str) -> Optional[Any]:
        """Get a service"""
        return self.services.get(service_name)
    
    def has(self, service_name: str) -> bool:
        """Check if service exists"""
        return service_name in self.services
    
    def unregister(self, service_name: str):
        """Remove a registered service"""
        if service_name in self.services:
            del self.services[service_name]
            self.providers.pop(service_name, None)
            logger.debug(f"Unregistered service {service_name}")
    
    def check_requirements(self, required: List[str]) -> List[str]:
        """Check which required services are missing"""
        return [s for s in required if s not in self.services]


class EnhancedPluginManager:
    """Enhanced plugin manager with dependency resolution and configuration"""
    
    def __init__(self, app: FastMCP, 
                 plugin_dir: str = "features",
                 config_dir: Optional[str] = None):
        self.app = app
        self.plugin_dir = Path(plugin_dir)
        self.config_manager = PluginConfigManager(config_dir)
        self.service_registry = ServiceRegistry()
        self.plugins: Dict[str, PluginInstance] = {}
        self.load_order: List[str] = []
        
        # Thread safety
        self._lock = threading.RLock()
        logger.debug("Initialized EnhancedPluginManager with thread safety")
    
    def discover_plugins(self) -> Dict[str, PluginInstance]:
        """Discover all available plugins"""
        plugins = {}
        
        # Add plugin directory to path if needed
        if str(self.plugin_dir.parent) not in sys.path:
            sys.path.insert(0, str(self.plugin_dir.parent))
        
        # Scan plugin directory
        for file_path in self.plugin_dir.glob("*.py"):
            if file_path.name.startswith('_'):
                continue
            
            module_name = f"{self.plugin_dir.name}.{file_path.stem}"
            
            try:
                # Import module
                module = importlib.import_module(module_name)
                
                # Find plugin classes
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, PluginBase) and 
                        obj != PluginBase and
                        hasattr(obj, 'register')):
                        
                        # Create plugin instance
                        metadata = PluginMetadata.from_plugin_class(obj)
                        config = self.config_manager.get_config(metadata.name)
                        
                        # Validate config if schema provided
                        if metadata.config_schema:
                            if not self.config_manager.validate_config(
                                config, metadata.config_schema
                            ):
                                logger.error(f"Invalid config for {metadata.name}")
                                continue
                        
                        plugin = PluginInstance(
                            plugin_class=obj,
                            metadata=metadata,
                            config=config
                        )
                        
                        plugins[metadata.name] = plugin
                        
            except Exception as e:
                logger.error(f"Failed to import {module_name}: {e}")
        
        return plugins
    
    def resolve_dependencies(self, plugins: Dict[str, PluginInstance]) -> List[PluginInstance]:
        """Resolve plugin dependencies and determine load order"""
        resolver = PluginDependencyResolver()
        
        # Add all plugins
        for plugin in plugins.values():
            resolver.add_plugin(plugin)
        
        # Check for missing dependencies
        missing = resolver.check_missing_dependencies()
        if missing:
            logger.warning(f"Missing plugin dependencies: {missing}")
            
            # Disable plugins with missing dependencies
            for plugin_name, deps in missing.items():
                plugin = plugins[plugin_name]
                plugin.state = "failed"
                plugin.error = f"Missing dependencies: {deps}"
        
        # Resolve load order
        try:
            return resolver.resolve()
        except ValueError as e:
            logger.error(f"Failed to resolve dependencies: {e}")
            raise
    
    def load_plugin(self, plugin: PluginInstance, 
                   services: Dict[str, Any]) -> bool:
        """Load a single plugin"""
        logger.info(f"Loading plugin: {plugin.metadata.name}")
        plugin.state = "loading"
        
        try:
            # Check service requirements
            missing_services = self.service_registry.check_requirements(
                plugin.metadata.required_services
            )
            if missing_services:
                raise ValueError(f"Missing required services: {missing_services}")
            
            # Add plugin-specific services
            plugin_services = {**services}
            
            # Add services from registry
            for service_name in plugin.metadata.required_services:
                if service_name not in plugin_services:
                    plugin_services[service_name] = self.service_registry.get(service_name)
            
            # Add plugin config
            plugin_services['config'] = plugin.config
            
            # Track registered tools/resources
            tools_before = set(self.app._tools.keys())
            resources_before = set(self.app._resources.keys())
            
            # Register the plugin
            plugin.plugin_class.register(self.app, plugin_services)
            
            # Track what was added
            plugin.provided_tools = list(
                set(self.app._tools.keys()) - tools_before
            )
            plugin.provided_resources = list(
                set(self.app._resources.keys()) - resources_before
            )
            
            # Register provided services
            for service_name in plugin.metadata.provides_services:
                # Plugin should set the service in services dict
                if service_name in plugin_services:
                    self.service_registry.register(
                        service_name,
                        plugin_services[service_name],
                        plugin.metadata.name
                    )
            
            plugin.state = "loaded"
            logger.info(
                f"Loaded plugin {plugin.metadata.name} "
                f"(tools: {len(plugin.provided_tools)}, "
                f"resources: {len(plugin.provided_resources)})"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin.metadata.name}: {e}")
            plugin.state = "failed"
            plugin.error = str(e)
            return False
    
    def load_all(self, services: Dict[str, Any]):
        """Load all plugins with dependency resolution"""
        with self._lock:
            # Discover plugins
            discovered = self.discover_plugins()
            logger.info(f"Discovered {len(discovered)} plugins")
            
            # Filter enabled plugins
            enabled_plugins = {
                name: plugin for name, plugin in discovered.items()
                if plugin.metadata.enabled
            }
            
            # Resolve dependencies
            load_order = self.resolve_dependencies(enabled_plugins)
            
            # Load plugins in order
            loaded = 0
            failed = 0
            
            for plugin in load_order:
                if plugin.state == "failed":
                    failed += 1
                    continue
                
                if self.load_plugin(plugin, services):
                    loaded += 1
                    self.plugins[plugin.metadata.name] = plugin
                    self.load_order.append(plugin.metadata.name)
                else:
                    failed += 1
            
            logger.info(f"Plugin loading complete: {loaded} loaded, {failed} failed")
    
    def unload_plugin(self, plugin_name: str):
        """Unload a plugin"""
        with self._lock:
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin {plugin_name} not loaded")
                return
            
            plugin = self.plugins[plugin_name]
            
            # Remove registered tools
            for tool in plugin.provided_tools:
                if hasattr(self.app, '_tools') and tool in self.app._tools:
                    del self.app._tools[tool]
                    logger.debug(f"Removed tool: {tool}")
            
            # Remove registered resources
            for resource in plugin.provided_resources:
                if hasattr(self.app, '_resources') and resource in self.app._resources:
                    del self.app._resources[resource]
                    logger.debug(f"Removed resource: {resource}")
            
            # Unregister provided services
            for service_name in plugin.metadata.provides_services:
                if self.service_registry.providers.get(service_name) == plugin_name:
                    self.service_registry.unregister(service_name)
                    logger.debug(f"Unregistered service: {service_name}")
            
            # Clear plugin's tracked items
            plugin.provided_tools.clear()
            plugin.provided_resources.clear()
            plugin.state = "unloaded"
            
            logger.info(f"Unloaded plugin: {plugin_name}")
    
    def reload_plugin(self, plugin_name: str, services: Dict[str, Any]):
        """Reload a plugin"""
        with self._lock:
            self.unload_plugin(plugin_name)
            
            # Re-discover in case code changed
            discovered = self.discover_plugins()
            if plugin_name in discovered:
                plugin = discovered[plugin_name]
                if self.load_plugin(plugin, services):
                    self.plugins[plugin.metadata.name] = plugin
    
    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """Get information about all plugins"""
        with self._lock:
            info = []
            
            for plugin in self.plugins.values():
                info.append({
                    "name": plugin.metadata.name,
                    "version": plugin.metadata.version,
                    "description": plugin.metadata.description,
                    "state": plugin.state,
                    "error": plugin.error,
                    "dependencies": plugin.metadata.dependencies,
                    "tools": plugin.provided_tools.copy(),  # Copy to avoid external modification
                    "resources": plugin.provided_resources.copy(),
                    "config": plugin.config.copy() if plugin.config else {}
                })
            
            return info
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get plugin dependency graph"""
        with self._lock:
            graph = {}
            
            for plugin in self.plugins.values():
                graph[plugin.metadata.name] = plugin.metadata.dependencies.copy()
            
            return graph