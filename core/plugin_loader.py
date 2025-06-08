import importlib
import pkgutil
from pathlib import Path
from typing import List, Type, Dict, Any
from fastmcp import FastMCP
import logging

logger = logging.getLogger(__name__)


class PluginBase:
    """Base class for all feature plugins"""
    
    @staticmethod
    def register(app: FastMCP, services: Dict[str, Any]):
        """Register tools and resources with the MCP app
        
        Args:
            app: The FastMCP application instance
            services: Dictionary of core services available to plugins
        """
        raise NotImplementedError


class PluginLoader:
    """Discovers and loads feature plugins"""
    
    @staticmethod
    def load_all(app: FastMCP, services: Dict[str, Any]):
        """Load all plugins from features/ directory
        
        Args:
            app: The FastMCP application instance
            services: Dictionary of core services to pass to plugins
        """
        features_path = Path(__file__).parent.parent / "features"
        
        # Ensure features directory exists
        if not features_path.exists():
            logger.warning(f"Features directory not found at {features_path}")
            return
        
        loaded_count = 0
        
        # Discover all Python modules in features/
        for _, module_name, _ in pkgutil.iter_modules([str(features_path)]):
            full_module_name = f"features.{module_name}"
            
            try:
                module = importlib.import_module(full_module_name)
                
                # Look for classes inheriting from PluginBase
                plugin_found = False
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, PluginBase) and 
                        attr != PluginBase):
                        # Register the plugin
                        plugin = attr()
                        plugin.register(app, services)
                        logger.info(f"Loaded plugin: {attr_name} from {module_name}")
                        loaded_count += 1
                        plugin_found = True
                
                # Also check for legacy register() function
                if not plugin_found and hasattr(module, 'register'):
                    # Support legacy plugins with register() function
                    register_func = getattr(module, 'register')
                    if callable(register_func):
                        # Adapt legacy register function
                        register_func(app)
                        logger.info(f"Loaded legacy plugin from {module_name}")
                        loaded_count += 1
                        
            except Exception as e:
                logger.error(f"Failed to load plugin from {full_module_name}: {e}")
        
        logger.info(f"Plugin loader: loaded {loaded_count} plugins")