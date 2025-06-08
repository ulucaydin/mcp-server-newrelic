#!/usr/bin/env python3
"""
New Relic MCP CLI - Command-line interface for direct tool execution

This CLI allows users to directly invoke MCP tools without going through
an AI assistant, useful for scripting and debugging.
"""

import asyncio
import click
import json
import os
import sys
from typing import Any, Dict, Optional
from pathlib import Path
import yaml

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import create_app
from core.account_manager import AccountManager
import logging

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'WARNING'),
    format='%(message)s'  # Simple format for CLI
)
logger = logging.getLogger(__name__)


class CLIContext:
    """Context object for CLI commands"""
    
    def __init__(self):
        self.app = None
        self.tools = {}
        self.resources = {}
    
    async def initialize(self):
        """Initialize the MCP app and discover tools"""
        self.app = await create_app()
        
        # Extract tools and resources from the app
        # This is a simplified approach - in reality we'd need to
        # inspect the FastMCP app's registered tools
        logger.debug("CLI initialized with MCP app")


pass_context = click.make_pass_decorator(CLIContext, ensure=True)


@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--account', '-a', help='New Relic account to use')
@pass_context
def cli(ctx: CLIContext, debug: bool, account: Optional[str]):
    """New Relic MCP CLI - Direct access to MCP tools
    
    Examples:
        nr-mcp query "SELECT count(*) FROM Transaction SINCE 1 hour ago"
        nr-mcp entities search --name "My Service"
        nr-mcp apm metrics "My App" --time-range "SINCE 30 minutes ago"
    """
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle account override
    if account:
        os.environ['NEW_RELIC_ACCOUNT_NAME'] = account


@cli.command()
@click.argument('nrql')
@click.option('--account-id', type=int, help='Account ID to query')
@pass_context
def query(ctx: CLIContext, nrql: str, account_id: Optional[int]):
    """Execute an NRQL query
    
    Example:
        nr-mcp query "SELECT count(*) FROM Transaction SINCE 1 hour ago"
    """
    async def run():
        await ctx.initialize()
        
        # Import here to avoid circular imports
        from features.common import CommonPlugin
        from core.nerdgraph_client import NerdGraphClient
        from core.account_manager import AccountManager
        
        # Get credentials
        account_manager = AccountManager()
        creds = account_manager.get_current_credentials()
        
        # Create NerdGraph client
        async with NerdGraphClient(creds["api_key"], creds["nerdgraph_url"]) as client:
            services = {
                "nerdgraph": client,
                "account_id": account_id or creds.get("account_id")
            }
            
            # Create a minimal app to register the tool
            from fastmcp import FastMCP
            app = FastMCP("cli-temp")
            CommonPlugin.register(app, services)
            
            # Execute the query
            result = await app._tools["run_nrql_query"](nrql, account_id)
            
            # Pretty print the result
            try:
                data = json.loads(result)
                if "actor" in data and "account" in data["actor"]:
                    nrql_data = data["actor"]["account"]["nrql"]
                    if "results" in nrql_data:
                        click.echo(json.dumps(nrql_data["results"], indent=2))
                    else:
                        click.echo(json.dumps(nrql_data, indent=2))
                else:
                    click.echo(result)
            except:
                click.echo(result)
    
    asyncio.run(run())


@cli.group()
def entities():
    """Entity management commands"""
    pass


@entities.command('search')
@click.option('--name', help='Entity name to search for')
@click.option('--type', 'entity_type', help='Entity type (e.g., APPLICATION, HOST)')
@click.option('--domain', help='Entity domain (e.g., APM, INFRA)')
@click.option('--tag', multiple=True, help='Tags to filter by (format: key=value)')
@click.option('--account-id', type=int, help='Account ID to search in')
@click.option('--limit', type=int, default=50, help='Maximum results')
@pass_context
def search_entities(ctx: CLIContext, name: Optional[str], entity_type: Optional[str],
                   domain: Optional[str], tag: list, account_id: Optional[int], limit: int):
    """Search for entities
    
    Example:
        nr-mcp entities search --name "My Service" --type APPLICATION
    """
    async def run():
        await ctx.initialize()
        
        from features.entities import EntitiesPlugin
        from core.nerdgraph_client import NerdGraphClient
        from core.account_manager import AccountManager
        
        # Parse tags
        tags_dict = []
        for t in tag:
            if '=' in t:
                key, value = t.split('=', 1)
                tags_dict.append({"key": key, "value": value})
        
        # Get credentials
        account_manager = AccountManager()
        creds = account_manager.get_current_credentials()
        
        async with NerdGraphClient(creds["api_key"], creds["nerdgraph_url"]) as client:
            services = {
                "nerdgraph": client,
                "account_id": account_id or creds.get("account_id"),
                "entity_definitions": None,
                "session_manager": None
            }
            
            from fastmcp import FastMCP
            app = FastMCP("cli-temp")
            EntitiesPlugin.register(app, services)
            
            # Execute search
            result = await app._tools["search_entities"](
                name=name,
                entity_type=entity_type,
                domain=domain,
                tags=tags_dict if tags_dict else None,
                target_account_id=account_id,
                limit=limit
            )
            
            # Pretty print results
            try:
                data = json.loads(result)
                if "actor" in data and "entitySearch" in data["actor"]:
                    entities = data["actor"]["entitySearch"]["results"]["entities"]
                    click.echo(f"Found {len(entities)} entities:\n")
                    for entity in entities:
                        click.echo(f"- {entity['name']} ({entity['entityType']})")
                        click.echo(f"  GUID: {entity['guid']}")
                        if entity.get('tags'):
                            tags_str = ", ".join([f"{t['key']}={t['value']}" for t in entity['tags'][:3]])
                            click.echo(f"  Tags: {tags_str}")
                        click.echo()
                else:
                    click.echo(result)
            except:
                click.echo(result)
    
    asyncio.run(run())


@entities.command('details')
@click.argument('guid')
@pass_context
def entity_details(ctx: CLIContext, guid: str):
    """Get details for a specific entity by GUID
    
    Example:
        nr-mcp entities details "MXxBUE18QVBQTElDQVRJT058MTIzNDU2"
    """
    async def run():
        await ctx.initialize()
        
        from features.entities import EntitiesPlugin
        from core.nerdgraph_client import NerdGraphClient
        from core.account_manager import AccountManager
        
        account_manager = AccountManager()
        creds = account_manager.get_current_credentials()
        
        async with NerdGraphClient(creds["api_key"], creds["nerdgraph_url"]) as client:
            services = {
                "nerdgraph": client,
                "account_id": creds.get("account_id"),
                "entity_definitions": None,
                "session_manager": None
            }
            
            from fastmcp import FastMCP
            app = FastMCP("cli-temp")
            EntitiesPlugin.register(app, services)
            
            # Get entity details
            result = await app._resources[f"newrelic://entity/{guid}"]()
            
            # Pretty print
            try:
                data = json.loads(result)
                if "actor" in data and "entity" in data["actor"]:
                    entity = data["actor"]["entity"]
                    click.echo(f"Entity: {entity['name']}")
                    click.echo(f"Type: {entity['entityType']}")
                    click.echo(f"Domain: {entity['domain']}")
                    click.echo(f"GUID: {entity['guid']}")
                    
                    if entity.get('alertSeverity'):
                        click.echo(f"Alert Severity: {entity['alertSeverity']}")
                    
                    if entity.get('tags'):
                        click.echo("\nTags:")
                        for tag in entity['tags']:
                            click.echo(f"  {tag['key']}: {tag['value']}")
                    
                    if entity.get('recentAlertViolations'):
                        click.echo("\nRecent Violations:")
                        for violation in entity['recentAlertViolations']:
                            click.echo(f"  - {violation['label']} ({violation['level']})")
                else:
                    click.echo(result)
            except:
                click.echo(result)
    
    asyncio.run(run())


@cli.group()
def apm():
    """APM commands"""
    pass


@apm.command('list')
@click.option('--account-id', type=int, help='Account ID')
@pass_context
def list_apm(ctx: CLIContext, account_id: Optional[int]):
    """List APM applications"""
    async def run():
        await ctx.initialize()
        
        from features.apm import APMPlugin
        from core.nerdgraph_client import NerdGraphClient
        from core.account_manager import AccountManager
        
        account_manager = AccountManager()
        creds = account_manager.get_current_credentials()
        
        async with NerdGraphClient(creds["api_key"], creds["nerdgraph_url"]) as client:
            services = {
                "nerdgraph": client,
                "account_id": account_id or creds.get("account_id"),
                "entity_definitions": None
            }
            
            from fastmcp import FastMCP
            app = FastMCP("cli-temp")
            APMPlugin.register(app, services)
            
            result = await app._tools["list_apm_applications"](account_id)
            
            # Pretty print
            try:
                data = json.loads(result)
                if "actor" in data:
                    entities = data["actor"]["entitySearch"]["results"]["entities"]
                    click.echo(f"Found {len(entities)} APM applications:\n")
                    for app in entities:
                        status = "🟢" if app.get('reporting') else "🔴"
                        click.echo(f"{status} {app['name']} ({app.get('language', 'Unknown')})")
                        if app.get('alertSeverity') and app['alertSeverity'] != 'NOT_ALERTING':
                            click.echo(f"   ⚠️  Alert: {app['alertSeverity']}")
                else:
                    click.echo(result)
            except:
                click.echo(result)
    
    asyncio.run(run())


@apm.command('metrics')
@click.argument('application_name')
@click.option('--metrics', '-m', multiple=True, help='Specific metrics to fetch')
@click.option('--time-range', default='SINCE 1 hour ago', help='NRQL time range')
@click.option('--account-id', type=int, help='Account ID')
@pass_context
def apm_metrics(ctx: CLIContext, application_name: str, metrics: tuple, 
                time_range: str, account_id: Optional[int]):
    """Get APM application metrics
    
    Example:
        nr-mcp apm metrics "My App" --time-range "SINCE 30 minutes ago"
    """
    async def run():
        await ctx.initialize()
        
        from features.apm import APMPlugin
        from core.nerdgraph_client import NerdGraphClient
        from core.account_manager import AccountManager
        
        account_manager = AccountManager()
        creds = account_manager.get_current_credentials()
        
        async with NerdGraphClient(creds["api_key"], creds["nerdgraph_url"]) as client:
            services = {
                "nerdgraph": client,
                "account_id": account_id or creds.get("account_id"),
                "entity_definitions": None
            }
            
            from fastmcp import FastMCP
            app = FastMCP("cli-temp")
            APMPlugin.register(app, services)
            
            result = await app._tools["get_apm_metrics"](
                application_name=application_name,
                metrics=list(metrics) if metrics else None,
                time_range=time_range,
                target_account_id=account_id
            )
            
            # Pretty print metrics
            click.echo(f"\nMetrics for {result['application']} ({result['time_range']}):\n")
            
            for metric, value in result['metrics'].items():
                if isinstance(value, dict) and 'error' not in value:
                    # Extract the numeric value
                    if 'result' in value:
                        val = value['result']
                    elif 'average.duration' in value:
                        val = f"{value['average.duration'] * 1000:.2f} ms"
                    elif 'percentage' in value:
                        val = f"{value['percentage']:.2f}%"
                    elif 'rate' in value:
                        val = f"{value['rate']:.2f} rpm"
                    elif 'apdex' in value:
                        val = f"{value['apdex']:.3f}"
                    else:
                        val = str(value)
                    
                    click.echo(f"  {metric}: {val}")
                elif isinstance(value, dict) and 'error' in value:
                    click.echo(f"  {metric}: ❌ {value['error']}")
                else:
                    click.echo(f"  {metric}: {value}")
    
    asyncio.run(run())


@cli.group()
def config():
    """Configuration management"""
    pass


@config.command('add-account')
@click.option('--name', prompt=True, help='Account name/alias')
@click.option('--api-key', prompt=True, hide_input=True, help='New Relic API key')
@click.option('--account-id', prompt=True, help='New Relic account ID')
@click.option('--region', type=click.Choice(['US', 'EU']), default='US', help='Region')
@click.option('--set-default', is_flag=True, help='Set as default account')
def add_account(name: str, api_key: str, account_id: str, region: str, set_default: bool):
    """Add a New Relic account configuration"""
    account_manager = AccountManager()
    account_manager.add_account(name, api_key, account_id, region, set_default)
    click.echo(f"✅ Account '{name}' added successfully")
    if set_default:
        click.echo(f"   Set as default account")


@config.command('list-accounts')
def list_accounts():
    """List configured accounts"""
    account_manager = AccountManager()
    accounts = account_manager.list_accounts()
    
    if not accounts:
        click.echo("No accounts configured. Use 'nr-mcp config add-account' to add one.")
        return
    
    click.echo("Configured accounts:\n")
    for name, info in accounts.items():
        default = " (current)" if info.get('is_current') else ""
        click.echo(f"  {name}{default}")
        click.echo(f"    Account ID: {info.get('account_id')}")
        click.echo(f"    Region: {info.get('region', 'US')}")
        click.echo(f"    API Key: {info.get('api_key', '***')}")
        click.echo()


@config.command('use')
@click.argument('account_name')
def use_account(account_name: str):
    """Switch to a different account"""
    account_manager = AccountManager()
    try:
        account_manager.switch_account(account_name)
        click.echo(f"✅ Switched to account '{account_name}'")
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def serve():
    """Start the MCP server (for debugging)"""
    click.echo("Starting New Relic MCP server...")
    asyncio.run(main.main())


@cli.command()
def version():
    """Show version information"""
    click.echo("New Relic MCP Server v1.0.0")
    click.echo("Model Context Protocol server for New Relic observability platform")


if __name__ == '__main__':
    cli()