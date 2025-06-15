#!/usr/bin/env python3
"""Command-line interface for the UDS Python client."""

import asyncio
import json
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from . import AsyncUDSClient, ClientConfig
from .models import ListSchemasOptions, SearchPatternsOptions

console = Console()


@click.group()
@click.option(
    "--base-url",
    envvar="UDS_BASE_URL",
    default="http://localhost:8080/api/v1",
    help="API base URL",
)
@click.option(
    "--api-key",
    envvar="UDS_API_KEY",
    help="API authentication key",
)
@click.option(
    "--timeout",
    type=float,
    default=30.0,
    help="Request timeout in seconds",
)
@click.pass_context
def cli(ctx, base_url: str, api_key: Optional[str], timeout: float):
    """New Relic UDS CLI - Command-line interface for the Unified Data Service."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = ClientConfig(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
    )


@cli.command()
@click.pass_context
def health(ctx):
    """Check API health status."""
    
    async def _health():
        async with AsyncUDSClient(ctx.obj["config"]) as client:
            try:
                health_status = await client.health()
                
                console.print(f"[green]✓[/green] API Status: {health_status.status}")
                console.print(f"Version: {health_status.version}")
                console.print(f"Uptime: {health_status.uptime}")
                
                if health_status.components:
                    console.print("\nComponents:")
                    for name, status in health_status.components.items():
                        console.print(f"  {name}: {status.get('status', 'unknown')}")
                
            except Exception as e:
                console.print(f"[red]✗[/red] Health check failed: {e}")
                sys.exit(1)
    
    asyncio.run(_health())


@cli.group()
def discovery():
    """Schema discovery commands."""
    pass


@discovery.command("list")
@click.option("--event-type", help="Filter by event type")
@click.option("--min-records", type=int, help="Minimum record count")
@click.option("--max-schemas", type=int, default=20, help="Maximum schemas to return")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_schemas(
    ctx,
    event_type: Optional[str],
    min_records: Optional[int],
    max_schemas: int,
    output_json: bool,
):
    """List discovered schemas."""
    
    async def _list_schemas():
        async with AsyncUDSClient(ctx.obj["config"]) as client:
            try:
                options = ListSchemasOptions(
                    event_type=event_type,
                    min_record_count=min_records,
                    max_schemas=max_schemas,
                    include_metadata=True,
                )
                
                response = await client.discovery.list_schemas(options)
                
                if output_json:
                    console.print(json.dumps(response.model_dump(), indent=2))
                else:
                    table = Table(title="Discovered Schemas")
                    table.add_column("Name", style="cyan")
                    table.add_column("Event Type", style="green")
                    table.add_column("Records", justify="right")
                    table.add_column("Quality", justify="right")
                    table.add_column("Attributes", justify="right")
                    
                    for schema in response.schemas:
                        table.add_row(
                            schema.name,
                            schema.event_type,
                            f"{schema.record_count:,}",
                            f"{schema.quality.overall_score:.2f}",
                            str(len(schema.attributes)),
                        )
                    
                    console.print(table)
                    
                    if response.metadata:
                        console.print(
                            f"\nTotal schemas: {response.metadata.total_schemas}"
                        )
                        console.print(
                            f"Execution time: {response.metadata.execution_time}"
                        )
                
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to list schemas: {e}")
                sys.exit(1)
    
    asyncio.run(_list_schemas())


@discovery.command("get")
@click.argument("schema_name")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def get_schema(ctx, schema_name: str, output_json: bool):
    """Get details of a specific schema."""
    
    async def _get_schema():
        async with AsyncUDSClient(ctx.obj["config"]) as client:
            try:
                schema = await client.discovery.get_schema(schema_name)
                
                if output_json:
                    console.print(json.dumps(schema.model_dump(), indent=2))
                else:
                    console.print(f"[bold]Schema: {schema.name}[/bold]")
                    console.print(f"Event Type: {schema.event_type}")
                    console.print(f"Record Count: {schema.record_count:,}")
                    console.print(
                        f"First Seen: {schema.first_seen.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    console.print(
                        f"Last Seen: {schema.last_seen.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    
                    console.print("\n[bold]Quality Metrics:[/bold]")
                    console.print(f"  Overall Score: {schema.quality.overall_score:.2f}")
                    console.print(f"  Completeness: {schema.quality.completeness:.2f}")
                    console.print(f"  Consistency: {schema.quality.consistency:.2f}")
                    console.print(f"  Validity: {schema.quality.validity:.2f}")
                    console.print(f"  Uniqueness: {schema.quality.uniqueness:.2f}")
                    
                    console.print(f"\n[bold]Attributes ({len(schema.attributes)}):[/bold]")
                    attr_table = Table()
                    attr_table.add_column("Name", style="cyan")
                    attr_table.add_column("Type", style="green")
                    attr_table.add_column("Nullable")
                    attr_table.add_column("Cardinality", justify="right")
                    
                    for attr in schema.attributes[:10]:  # Show first 10
                        attr_table.add_row(
                            attr.name,
                            attr.data_type,
                            "Yes" if attr.nullable else "No",
                            f"{attr.cardinality:,}",
                        )
                    
                    console.print(attr_table)
                    
                    if len(schema.attributes) > 10:
                        console.print(
                            f"\n... and {len(schema.attributes) - 10} more attributes"
                        )
                
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to get schema: {e}")
                sys.exit(1)
    
    asyncio.run(_get_schema())


@cli.group()
def patterns():
    """Pattern management commands."""
    pass


@patterns.command("search")
@click.option("--query", help="Search query")
@click.option("--category", help="Filter by category")
@click.option("--tags", multiple=True, help="Filter by tags")
@click.option("--limit", type=int, default=20, help="Maximum results")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def search_patterns(
    ctx,
    query: Optional[str],
    category: Optional[str],
    tags: tuple,
    limit: int,
    output_json: bool,
):
    """Search for patterns."""
    
    async def _search_patterns():
        async with AsyncUDSClient(ctx.obj["config"]) as client:
            try:
                options = SearchPatternsOptions(
                    query=query,
                    category=category,
                    tags=list(tags) if tags else None,
                    limit=limit,
                )
                
                response = await client.patterns.search(options)
                
                if output_json:
                    console.print(json.dumps(response.model_dump(), indent=2))
                else:
                    table = Table(title=f"Patterns (Total: {response.total})")
                    table.add_column("ID", style="cyan")
                    table.add_column("Name", style="green")
                    table.add_column("Category")
                    table.add_column("Tags")
                    
                    for pattern in response.patterns:
                        table.add_row(
                            pattern.id,
                            pattern.name,
                            pattern.category,
                            ", ".join(pattern.tags) if pattern.tags else "",
                        )
                    
                    console.print(table)
                
            except Exception as e:
                console.print(f"[red]✗[/red] Failed to search patterns: {e}")
                sys.exit(1)
    
    asyncio.run(_search_patterns())


def main():
    """Main entry point."""
    try:
        # Add rich exception handling
        from rich.traceback import install
        install(show_locals=False)
    except ImportError:
        pass
    
    cli()


if __name__ == "__main__":
    main()