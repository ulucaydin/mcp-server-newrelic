"""
Tests for plugin system and feature plugins
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
import os
import sys

from fastmcp import FastMCP
from core.plugin_loader import PluginBase, PluginLoader

# Import feature plugins
from features.common import CommonPlugin
from features.entities import EntitiesPlugin
from features.apm import APMPlugin
from features.alerts import AlertsPlugin
from features.synthetics import SyntheticsPlugin


class TestPluginLoader:
    """Test plugin loading system"""
    
    @pytest.fixture
    def test_app(self):
        """Create test FastMCP app"""
        return FastMCP(
            name="test-app",
            version="1.0.0"
        )
    
    def test_plugin_discovery(self, test_app):
        """Test plugin discovery in features directory"""
        plugins = PluginLoader.discover_plugins()
        
        # Should find at least the core plugins
        assert len(plugins) >= 5
        plugin_names = [p.__name__ for p in plugins]
        
        assert 'CommonPlugin' in plugin_names
        assert 'EntitiesPlugin' in plugin_names
        assert 'APMPlugin' in plugin_names
        assert 'AlertsPlugin' in plugin_names
        assert 'SyntheticsPlugin' in plugin_names
    
    def test_load_single_plugin(self, test_app, test_services):
        """Test loading a single plugin"""
        # Clear loaded plugins
        PluginLoader.loaded_plugins.clear()
        
        # Load common plugin
        PluginLoader.load_plugin(CommonPlugin, test_app, test_services)
        
        # Should be registered
        assert CommonPlugin in PluginLoader.loaded_plugins
        
        # Should have registered tools
        assert len(test_app._tools) > 0
    
    def test_load_all_plugins(self, test_app, test_services):
        """Test loading all plugins"""
        PluginLoader.loaded_plugins.clear()
        
        PluginLoader.load_all(test_app, test_services)
        
        # Should have loaded multiple plugins
        assert len(PluginLoader.loaded_plugins) >= 5
        
        # Should have registered many tools
        assert len(test_app._tools) > 10
    
    def test_plugin_error_handling(self, test_app, test_services):
        """Test error handling during plugin loading"""
        # Create a bad plugin
        class BadPlugin(PluginBase):
            @staticmethod
            def register(app, services):
                raise Exception("Plugin load error")
        
        # Should log error but not crash
        with patch('logging.Logger.error') as mock_log:
            PluginLoader.load_plugin(BadPlugin, test_app, test_services)
            mock_log.assert_called()
        
        # Plugin should not be in loaded list
        assert BadPlugin not in PluginLoader.loaded_plugins


class TestCommonPlugin:
    """Test common plugin functionality"""
    
    @pytest.mark.asyncio
    async def test_query_nerdgraph(self, test_app, test_services):
        """Test NerdGraph query tool"""
        CommonPlugin.register(test_app, test_services)
        
        # Get the tool
        tool = test_app._tools.get("query_nerdgraph")
        assert tool is not None
        
        # Set up mock response
        test_services["nerdgraph"].query.return_value = {
            "actor": {"user": {"email": "test@example.com"}}
        }
        
        # Call the tool
        result = await tool["handler"](
            nerdgraph_query="{ actor { user { email } } }"
        )
        
        # Should return JSON string
        result_data = json.loads(result)
        assert "actor" in result_data
        assert result_data["actor"]["user"]["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_run_nrql_query(self, test_app, test_services):
        """Test NRQL query tool"""
        CommonPlugin.register(test_app, test_services)
        
        tool = test_app._tools.get("run_nrql_query")
        assert tool is not None
        
        # Set up mock response
        test_services["nerdgraph"].query.return_value = {
            "actor": {
                "account": {
                    "nrql": {
                        "results": [{"count": 1000}]
                    }
                }
            }
        }
        
        # Call the tool
        result = await tool["handler"](
            nrql="SELECT count(*) FROM Transaction",
            target_account_id=123456
        )
        
        result_data = json.loads(result)
        assert "actor" in result_data
    
    @pytest.mark.asyncio
    async def test_nrql_without_account(self, test_app, test_services):
        """Test NRQL query without account ID"""
        # Remove default account
        test_services["account_id"] = None
        
        CommonPlugin.register(test_app, test_services)
        tool = test_app._tools.get("run_nrql_query")
        
        # Should return error
        result = await tool["handler"](
            nrql="SELECT count(*) FROM Transaction"
        )
        
        result_data = json.loads(result)
        assert "errors" in result_data


class TestEntitiesPlugin:
    """Test entities plugin functionality"""
    
    @pytest.mark.asyncio
    async def test_search_entities(self, test_app, test_services):
        """Test entity search tool"""
        EntitiesPlugin.register(test_app, test_services)
        
        tool = test_app._tools.get("search_entities")
        assert tool is not None
        
        # Set up mock response
        test_services["nerdgraph"].query.return_value = {
            "actor": {
                "entitySearch": {
                    "results": {
                        "entities": [
                            {
                                "guid": "MTIzfEFQTXxBUFBMSUNBVElPTnw0NTY",
                                "name": "Test App",
                                "entityType": "APM_APPLICATION",
                                "domain": "APM"
                            }
                        ]
                    },
                    "count": 1
                }
            }
        }
        
        # Search by name
        result = await tool["handler"](
            name="Test",
            entity_type="APPLICATION",
            limit=10
        )
        
        result_data = json.loads(result)
        assert "actor" in result_data
        entities = result_data["actor"]["entitySearch"]["results"]["entities"]
        assert len(entities) == 1
        assert entities[0]["name"] == "Test App"
    
    @pytest.mark.asyncio
    async def test_search_entities_no_criteria(self, test_app, test_services):
        """Test entity search without criteria"""
        EntitiesPlugin.register(test_app, test_services)
        tool = test_app._tools.get("search_entities")
        
        # Should return error
        result = await tool["handler"]()
        
        result_data = json.loads(result)
        assert "errors" in result_data
        assert "search criterion" in result_data["errors"][0]["message"]
    
    @pytest.mark.asyncio
    async def test_get_entity_details(self, test_app, test_services):
        """Test getting entity details"""
        EntitiesPlugin.register(test_app, test_services)
        
        # Get resource handler
        resource = test_app._resources.get("newrelic://entity/{guid}")
        assert resource is not None
        
        # Set up mock response
        test_services["nerdgraph"].query.return_value = {
            "actor": {
                "entity": {
                    "guid": "MTIzfEFQTXxBUFBMSUNBVElPTnw0NTY",
                    "name": "Test App",
                    "entityType": "APM_APPLICATION",
                    "language": "java",
                    "reporting": True
                }
            }
        }
        
        # Get entity details
        result = await resource["handler"](
            guid="MTIzfEFQTXxBUFBMSUNBVElPTnw0NTY"
        )
        
        result_data = json.loads(result)
        assert "actor" in result_data
        assert result_data["actor"]["entity"]["name"] == "Test App"


class TestAPMPlugin:
    """Test APM plugin functionality"""
    
    @pytest.mark.asyncio
    async def test_list_apm_applications(self, test_app, test_services):
        """Test listing APM applications"""
        APMPlugin.register(test_app, test_services)
        
        tool = test_app._tools.get("list_apm_applications")
        assert tool is not None
        
        # Set up mock response
        test_services["nerdgraph"].query.return_value = {
            "actor": {
                "entitySearch": {
                    "results": {
                        "entities": [
                            {
                                "guid": "MTIzfEFQTXxBUFBMSUNBVElPTnw0NTY",
                                "name": "Test App",
                                "language": "java",
                                "reporting": True
                            }
                        ]
                    },
                    "count": 1
                }
            }
        }
        
        result = await tool["handler"](target_account_id=123456)
        
        result_data = json.loads(result)
        assert "actor" in result_data
    
    @pytest.mark.asyncio
    async def test_get_apm_metrics(self, test_app, test_services):
        """Test getting APM metrics"""
        APMPlugin.register(test_app, test_services)
        
        tool = test_app._tools.get("get_apm_metrics")
        assert tool is not None
        
        # Set up mock for multiple metric queries
        test_services["nerdgraph"].query.side_effect = [
            # Throughput query response
            {
                "actor": {
                    "account": {
                        "nrql": {
                            "results": [{"rate.count": 120}]
                        }
                    }
                }
            },
            # Response time query response
            {
                "actor": {
                    "account": {
                        "nrql": {
                            "results": [{"average.duration": 0.21}]
                        }
                    }
                }
            },
            # Error rate query response
            {
                "actor": {
                    "account": {
                        "nrql": {
                            "results": [{"percentage": 0.5}]
                        }
                    }
                }
            },
            # Apdex query response
            {
                "actor": {
                    "account": {
                        "nrql": {
                            "results": [{"apdex": 0.95}]
                        }
                    }
                }
            }
        ]
        
        result = await tool["handler"](
            application_name="Test App",
            time_range="SINCE 1 hour ago"
        )
        
        assert result["application"] == "Test App"
        assert "metrics" in result
        assert len(result["metrics"]) == 4


class TestAlertsPlugin:
    """Test alerts plugin functionality"""
    
    @pytest.mark.asyncio
    async def test_list_alert_policies(self, test_app, test_services):
        """Test listing alert policies"""
        AlertsPlugin.register(test_app, test_services)
        
        tool = test_app._tools.get("list_alert_policies")
        assert tool is not None
        
        # Set up mock response
        test_services["nerdgraph"].query.return_value = {
            "actor": {
                "account": {
                    "alerts": {
                        "policiesSearch": {
                            "policies": [
                                {
                                    "id": "123",
                                    "name": "Default Policy",
                                    "incidentPreference": "PER_POLICY"
                                }
                            ],
                            "totalCount": 1
                        }
                    }
                }
            }
        }
        
        result = await tool["handler"](target_account_id=123456)
        
        result_data = json.loads(result)
        assert "actor" in result_data
    
    @pytest.mark.asyncio
    async def test_list_open_incidents(self, test_app, test_services):
        """Test listing open incidents"""
        AlertsPlugin.register(test_app, test_services)
        
        tool = test_app._tools.get("list_open_incidents")
        assert tool is not None
        
        # Mock response with sample incident
        mock_response = {
            "actor": {
                "account": {
                    "alerts": {
                        "incidents": {
                            "incidents": [
                                {
                                    "incidentId": "INC-001",
                                    "title": "High Error Rate",
                                    "priority": "CRITICAL",
                                    "state": "OPEN"
                                }
                            ],
                            "totalCount": 1
                        }
                    }
                }
            }
        }
        
        test_services["nerdgraph"].query.return_value = mock_response
        
        result = await tool["handler"](
            target_account_id=123456,
            priority="CRITICAL"
        )
        
        result_data = json.loads(result)
        incidents = result_data["actor"]["account"]["alerts"]["incidents"]["incidents"]
        assert len(incidents) == 1
        assert incidents[0]["priority"] == "CRITICAL"


class TestSyntheticsPlugin:
    """Test synthetics plugin functionality"""
    
    @pytest.mark.asyncio
    async def test_list_synthetics_monitors(self, test_app, test_services):
        """Test listing synthetic monitors"""
        SyntheticsPlugin.register(test_app, test_services)
        
        tool = test_app._tools.get("list_synthetics_monitors")
        assert tool is not None
        
        # Set up mock response
        test_services["nerdgraph"].query.return_value = {
            "actor": {
                "entitySearch": {
                    "results": {
                        "entities": [
                            {
                                "guid": "MTIzfFNZTlRIfE1PTklUT1J8NDU2",
                                "name": "Test Monitor",
                                "monitorType": "SIMPLE_BROWSER",
                                "status": "ENABLED"
                            }
                        ]
                    },
                    "count": 1
                }
            }
        }
        
        result = await tool["handler"](target_account_id=123456)
        
        result_data = json.loads(result)
        assert "actor" in result_data
        entities = result_data["actor"]["entitySearch"]["results"]["entities"]
        assert len(entities) == 1
        assert entities[0]["monitorType"] == "SIMPLE_BROWSER"