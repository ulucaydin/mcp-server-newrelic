"""
Tests for plugin unloading functionality
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from core.plugin_manager import (
    EnhancedPluginManager, PluginInstance, PluginMetadata,
    ServiceRegistry
)
from core.plugin_loader import PluginBase
from fastmcp import FastMCP


class TestPluginUnloading:
    """Test plugin unloading and cleanup"""
    
    @pytest.fixture
    def mock_app(self):
        """Create mock FastMCP app"""
        app = MagicMock(spec=FastMCP)
        app._tools = {
            "test_tool_1": Mock(),
            "test_tool_2": Mock(),
            "other_tool": Mock()
        }
        app._resources = {
            "test://resource/1": Mock(),
            "test://resource/2": Mock(),
            "other://resource": Mock()
        }
        return app
    
    @pytest.fixture
    def plugin_metadata(self):
        """Create test plugin metadata"""
        return PluginMetadata(
            name="TestPlugin",
            version="1.0.0",
            description="Test plugin",
            dependencies=[],
            required_services=[],
            provides_services=["test_service"],
            enabled=True
        )
    
    @pytest.fixture
    def plugin_instance(self, plugin_metadata):
        """Create test plugin instance"""
        plugin_class = type("TestPlugin", (PluginBase,), {
            "register": staticmethod(lambda app, services: None)
        })
        
        instance = PluginInstance(
            plugin_class=plugin_class,
            metadata=plugin_metadata,
            config={},
            state="loaded"
        )
        
        # Set provided tools and resources
        instance.provided_tools = ["test_tool_1", "test_tool_2"]
        instance.provided_resources = ["test://resource/1", "test://resource/2"]
        
        return instance
    
    def test_unload_plugin_removes_tools(self, mock_app, plugin_instance):
        """Test that unloading removes registered tools"""
        manager = EnhancedPluginManager(mock_app)
        manager.plugins["TestPlugin"] = plugin_instance
        
        # Unload the plugin
        manager.unload_plugin("TestPlugin")
        
        # Check tools were removed
        assert "test_tool_1" not in mock_app._tools
        assert "test_tool_2" not in mock_app._tools
        assert "other_tool" in mock_app._tools  # Other tools remain
        
        # Check plugin state
        assert plugin_instance.state == "unloaded"
        assert len(plugin_instance.provided_tools) == 0
    
    def test_unload_plugin_removes_resources(self, mock_app, plugin_instance):
        """Test that unloading removes registered resources"""
        manager = EnhancedPluginManager(mock_app)
        manager.plugins["TestPlugin"] = plugin_instance
        
        # Unload the plugin
        manager.unload_plugin("TestPlugin")
        
        # Check resources were removed
        assert "test://resource/1" not in mock_app._resources
        assert "test://resource/2" not in mock_app._resources
        assert "other://resource" in mock_app._resources  # Other resources remain
        
        # Check plugin state
        assert len(plugin_instance.provided_resources) == 0
    
    def test_unload_plugin_unregisters_services(self, mock_app, plugin_instance):
        """Test that unloading unregisters provided services"""
        manager = EnhancedPluginManager(mock_app)
        manager.plugins["TestPlugin"] = plugin_instance
        
        # Register the service
        manager.service_registry.register("test_service", Mock(), "TestPlugin")
        
        # Unload the plugin
        manager.unload_plugin("TestPlugin")
        
        # Check service was unregistered
        assert not manager.service_registry.has("test_service")
    
    def test_unload_nonexistent_plugin(self, mock_app):
        """Test unloading a plugin that doesn't exist"""
        manager = EnhancedPluginManager(mock_app)
        
        # Should not raise error
        manager.unload_plugin("NonExistentPlugin")
    
    def test_reload_plugin(self, mock_app, plugin_instance):
        """Test reloading a plugin"""
        manager = EnhancedPluginManager(mock_app)
        manager.plugins["TestPlugin"] = plugin_instance
        
        # Mock discover_plugins to return the same plugin
        with patch.object(manager, 'discover_plugins') as mock_discover:
            mock_discover.return_value = {"TestPlugin": plugin_instance}
            
            # Mock load_plugin
            with patch.object(manager, 'load_plugin') as mock_load:
                mock_load.return_value = True
                
                # Reload the plugin
                services = {"test": "service"}
                manager.reload_plugin("TestPlugin", services)
                
                # Check unload was called (tools/resources removed)
                assert len(plugin_instance.provided_tools) == 0
                assert len(plugin_instance.provided_resources) == 0
                
                # Check load was called
                mock_load.assert_called_once_with(plugin_instance, services)


class TestServiceRegistry:
    """Test service registry functionality"""
    
    def test_register_service(self):
        """Test registering a service"""
        registry = ServiceRegistry()
        service = Mock()
        
        registry.register("test_service", service, "TestProvider")
        
        assert registry.has("test_service")
        assert registry.get("test_service") is service
        assert registry.providers["test_service"] == "TestProvider"
    
    def test_unregister_service(self):
        """Test unregistering a service"""
        registry = ServiceRegistry()
        service = Mock()
        
        # Register then unregister
        registry.register("test_service", service, "TestProvider")
        registry.unregister("test_service")
        
        assert not registry.has("test_service")
        assert registry.get("test_service") is None
        assert "test_service" not in registry.providers
    
    def test_unregister_nonexistent_service(self):
        """Test unregistering a service that doesn't exist"""
        registry = ServiceRegistry()
        
        # Should not raise error
        registry.unregister("nonexistent")
    
    def test_override_service(self):
        """Test overriding an existing service"""
        registry = ServiceRegistry()
        service1 = Mock()
        service2 = Mock()
        
        registry.register("test_service", service1, "Provider1")
        registry.register("test_service", service2, "Provider2")
        
        assert registry.get("test_service") is service2
        assert registry.providers["test_service"] == "Provider2"
    
    def test_check_requirements(self):
        """Test checking for missing service requirements"""
        registry = ServiceRegistry()
        
        registry.register("service1", Mock(), "Provider1")
        registry.register("service2", Mock(), "Provider2")
        
        # Check with all requirements met
        missing = registry.check_requirements(["service1", "service2"])
        assert len(missing) == 0
        
        # Check with missing requirements
        missing = registry.check_requirements(["service1", "service3", "service4"])
        assert len(missing) == 2
        assert "service3" in missing
        assert "service4" in missing