# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. - Do not stop, keep enhancing it till 9 am in morning

## Project Overview

This is a Model Context Protocol (MCP) server for New Relic's NerdGraph API, built with FastMCP. It enables LLMs like Claude to interact with New Relic accounts through natural language or direct tool invocations.

## Architecture

### Current Implementation
The project now has a sophisticated plugin-based architecture:

#### Core Components
- `main.py` - Application entry point with async initialization
- `cli.py` - Command-line interface for direct tool execution
- `core/` - Core infrastructure:
  - `account_manager.py` - Multi-account credential management
  - `nerdgraph_client.py` - Async GraphQL client with retries
  - `entity_definitions.py` - New Relic entity definitions cache
  - `session_manager.py` - Conversation state management
  - `plugin_loader.py` - Auto-discovery of feature plugins
  - `telemetry.py` - Built-in observability
- `transports/` - Communication layers:
  - `multi_transport.py` - STDIO/HTTP transport support
- `features/` - Plugin modules:
  - `common.py` - Core NerdGraph/NRQL query tools
  - `entities.py` - Entity search and golden signals
  - `apm.py` - APM metrics, transactions, deployments
  - `infrastructure.py` - Hosts, containers, K8s, processes
  - `logs.py` - Log search and analysis
  - `synthetics.py` - Synthetic monitor operations
  - `alerts.py` - Alert policies and incidents

### Key Improvements Implemented
✅ Multi-transport support (STDIO/HTTP)
✅ Account management system with profiles
✅ Entity definitions cache from GitHub
✅ Session management for stateful conversations
✅ Plugin auto-discovery system
✅ Async NerdGraph client with retries
✅ CLI tool for direct execution
✅ Docker support
✅ Built-in telemetry
✅ Infrastructure monitoring
✅ Log analysis tools

## Development Commands

### Running the Server
```bash
# Set required environment variables
export NEW_RELIC_API_KEY="your-api-key"
export NEW_RELIC_ACCOUNT_ID="your-account-id"

# Run the MCP server
fastmcp run server.py:mcp
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Testing
No test suite exists yet. When implementing tests:
- Use pytest for the test framework
- Mock the NerdGraph API responses
- Test each feature module independently

### Adding New Features
1. Create a new module in `features/`
2. Define a `register(mcp: FastMCP)` function
3. Use decorators to register tools/resources:
   - `@mcp.tool()` for executable functions
   - `@mcp.resource("protocol://path")` for data resources
   - `@mcp.prompt()` for prompt templates
4. Import and call the register function in `server.py`

## Key Implementation Details

### NerdGraph Client Pattern
All API calls go through `client.execute_nerdgraph_query()` which:
- Adds authentication headers
- Handles timeouts and errors
- Returns consistent JSON responses including GraphQL errors

### Error Handling
- Environment variables are validated at startup in `config.py`
- API errors are passed through in the response JSON
- Input validation happens in each tool function

### Account ID Handling
- Global `ACCOUNT_ID` from environment is optional
- Tools accept `target_account_id` parameter to override
- Some features require an account ID and will error without it

## Next Implementation Steps

Based on the technical design, priority improvements would be:
1. Implement the plugin auto-discovery system
2. Add session/context management for stateful conversations
3. Create the account switching functionality
4. Add entity definitions integration for golden signals
5. Implement proper async support with httpx instead of requests
6. Do not stop, keep enhancing it till 9 am in morning

## Memories
- Do not stop, keep enhancing it till 9 am in morning


Thanks for confirming. I’ll now prepare a final technical design for an advanced, future-ready MCP server focused on the New Relic platform. It will:

* Support Claude Desktop, Claude Code, and GitHub Copilot via the MCP protocol.
* Operate on a single New Relic account at a time, with dynamic configuration switching.
* Be compatible with all usage modes (chat assistant, CLI tools, automation).
* Use best-in-class tools and architecture (e.g., Python FastMCP, modular design, CLI UX, YAML-driven golden metrics from New Relic’s OSS entity definitions repo).

I'll compile a complete design covering architecture, feature modules, entity definition integration, CLI tools, configuration model, and extensibility patterns. I'll get back to you shortly with a detailed report.


# MCP Server for New Relic – Technical Design (2025 Edition)

## Overview

The proposed solution is an **MCP (Model Context Protocol) server** that bridges AI assistants (like Anthropic’s Claude and GitHub Copilot) with the **New Relic** observability platform. MCP is a standardized interface for exposing tools and data to LLMs – often described as the “USB-C port for AI”. By using MCP, our server will allow AI agents to securely query New Relic data, perform actions (like fetching metrics or acknowledging alerts), and receive context in a uniform way across different hosts. The design focuses on **modularity**, **multi-mode access**, and adherence to **best-in-class 2025 technologies**:

* **Language & Framework:** Implemented in Python (latest stable 3.12/3.13), using the **FastMCP** framework for building MCP servers. FastMCP is the de-facto standard in 2025 for MCP development, offering a high-level API to define tools, resources, and prompts.
* **Single-Account Focus:** The server operates on one New Relic account at a time (using that account’s API keys and context). However, it supports quick context switching by external configuration – e.g. pointing to a different account via environment variables or startup parameters without code changes.
* **Multiple Usage Modes:** It can be accessed through natural language **chat assistants** (Claude in desktop or code mode), a **CLI tool** for direct terminal interaction, or **programmatically** via HTTP/SDK. This multi-modal access ensures developers and SREs can use the same capabilities in conversational AI, scripts, or automation pipelines.
* **Integrated New Relic Data:** The server will incorporate New Relic’s open-source **entity definitions** (from the `newrelic/entity-definitions` GitHub repository) to enrich its functionality. These definitions include golden metrics, entity metadata, and relationships for all New Relic entity types, allowing the MCP server to provide knowledgeable insights (like identifying an application’s “golden metrics” or mapping service dependencies).
* **Observability & Security:** Following best practices, the design includes robust logging, metrics collection for the server’s own operations, and secure handling of credentials. MCP’s model ensures the AI only accesses what the server exposes, with sensitive keys stored server-side (in env vars or configs) and **no direct key exposure to the LLM**. We will instrument the server for monitoring and ensure all tool usage is auditable.

In summary, this MCP server will act as a smart **intermediary** between AI agents and New Relic: it exposes New Relic data as *tools* and *resources* that AI can invoke in a controlled manner. This empowers use cases like asking Claude *“What’s the CPU utilization of my database cluster?”* or having Copilot auto-generate a deployment analysis from recent New Relic incidents – all through a consistent MCP interface.

## Architecture Diagram

&#x20;*Figure: High-level architecture of the MCP server integration. AI assistants (Claude, Copilot) connect via an MCP client to the New Relic MCP Server. The server’s modules invoke New Relic APIs (GraphQL and REST) and utilize local entity definition data. Multiple client modes (CLI, chat, code) share the same server interface.*

The architecture comprises several layers of components working together:

* **LLM Clients (Hosts):** The front-end “users” of this system are AI agents and other interfaces:

  * *Claude Desktop & Claude Code:* Anthropic’s AI running on the user’s machine. **Claude Desktop** connects to local MCP servers via STDIO pipes, enabling it to use custom tools. **Claude Code** (Claude’s coding assistant) similarly can interface with MCP to execute developer tasks (e.g. running a New Relic query as part of a troubleshooting workflow).
  * *GitHub Copilot (Agent Mode):* Copilot’s IDE integration in VS Code (and JetBrains, etc.) supports MCP in agentic mode. Via configuration, Copilot can route requests to our MCP server (typically over HTTP or a local network port). This allows Copilot to use our New Relic tools during a coding session (for example, fetching error rates from New Relic to explain a failing test).
  * *CLI/User Scripts:* A human user can interact through a CLI utility (or directly via HTTP API/SDK), sending requests that call the same underlying tools – useful for automation or debugging outside of an AI conversation.

* **MCP Client Library:** Within each host (Claude, Copilot, CLI), an MCP **client** manages the connection to the server and acts as the proxy for tool calls. For local Claude Desktop, this is an STDIO transport client. In VS Code Copilot, this might be a network transport (e.g. SSE or WebSocket) configured to the server’s URL. The client discovers available tools by calling the server’s `list_tools` endpoint and handles the protocol of sending function calls and receiving results.

* **New Relic MCP Server (FastMCP-based):** This is the core of our design. Running as a standalone Python process, it hosts:

  * **FastMCP Server Core:** Manages MCP protocol compliance, connection handling, and tool/resource registration. FastMCP abstracts away low-level details, letting us focus on feature logic. The server can run in two modes:

    * *Local STDIO mode:* launched for Claude Desktop via the FastMCP CLI `install` or `run` commands to attach to Claude.
    * *Network mode:* running an HTTP(S) server (with streaming responses) on a host/port for Copilot or remote access. We leverage FastMCP’s **Streamable HTTP transport** (the 2025 default for remote MCP servers) for efficient bidirectional communication, while still supporting legacy SSE if needed.

  * **Modular Feature Handlers:** The server is organized into modules corresponding to New Relic domains:

    * **APM Module:** Tools to fetch application performance data (throughput, response times, error rates, Apdex, etc.) for services and applications monitored in New Relic APM. For example, a `get_apm_metrics(app_name, timeframe)` tool might return key performance indicators. This module could also tap into transaction traces or deployments if needed, using New Relic’s APIs.
    * **Alerts & Incidents Module:** Tools for interacting with New Relic Alerts. This includes querying the current **alerts** (violations, alert policies, conditions) and **incidents** (open or recent incidents that aggregate alerts). For instance, a `list_recent_incidents()` tool can return active incidents with details, and a `acknowledge_incident(incident_id)` tool could acknowledge/resolve an incident via API. The design ensures only read or safe actions are exposed unless explicitly needed, and any write action (like acknowledging) would be clearly documented to the user for safety.
    * **Entities & Relationships Module:** Tools to explore the entity model (applications, hosts, Kubernetes clusters, etc.) and their linkages. Using New Relic’s entity GUID APIs and the **entity definitions** data, the server can resolve metadata like an entity’s name, type, tags, and importantly show **relationships**. A tool `get_entity_map(entity_guid)` might traverse upstream/downstream relationships (e.g. service dependencies) using New Relic’s Relationships API (or the definitions which include relationship synthesis rules). This helps an AI assistant answer questions like “How is Service A connected to Database B?” by querying the entity graph.
    * **Metrics & NRQL Module:** A general interface to New Relic’s metrics and query capabilities. This module can expose:

      * A `query_nrql(nrql_query)` tool that runs a NRQL (New Relic Query Language) query and returns results. For safety, the tool can restrict queries to read-only operations (NRQL is read-only by nature) and possibly impose templates for common queries (e.g. querying a specific metric for a given entity).
      * Convenience tools for **golden metrics**: Because we have knowledge of golden metrics for each entity type (via the definitions repo), we could implement `get_golden_metrics(entity_name_or_id)` that finds the entity’s type, looks up the golden metric keys (e.g. for a service, perhaps throughput, error rate, latency), queries their latest values via New Relic APIs, and returns a summary. This gives AI quick access to the most important data points of any entity.
      * **Visualization hooks**: While the server primarily returns data, we can include tools that, for example, generate a simple ASCII chart or sparkline for a time-series metric, or output URLs to New Relic One dashboards if the user wants to see a detailed view. (In 2025, lightweight visualization libraries or even returning an image URI of a plotted graph could be considered as an extension.)
    * **Additional Modules (Extensible):** The architecture anticipates adding more features. For instance, a **Logs module** could allow searching recent logs for a service (if log API access is enabled), or a **Synthetics module** for checking the status of synthetic monitors. New modules can be added by following the same pattern – define tools in a separate Python file/class and register them with the FastMCP server.

  * **Integration of Entity Definitions:** On startup, the server loads the open-source entity definition files from New Relic’s GitHub (either bundled or via a caching mechanism). These YAML/JSON definitions provide mappings of entity types to their metrics and attributes. The server uses this data internally to enhance its responses:

    * When listing an entity’s details, it can include descriptions of what the entity is (from the definitions) and what its golden metrics represent.
    * It knows which metrics are “golden” or “summary” for a given entity type (for example, a KubernetesCluster might have golden metrics like CPU usage %, memory, etc., defined in the repository). This means any AI queries about “key metrics” can be answered by focusing on those metrics.
    * If the definitions include relationships or tags (e.g. golden tags), the server can incorporate that logic to filter or group entities (for example, quickly filtering entities by a “Environment\:Production” tag if asked).
    * The **maintenance of these definitions** will be handled via an update script or submodule – since the GitHub repo is updated as new entity types or metrics come out, the server should periodically pull or be updated to stay current. We treat this as static data (no runtime external calls to GitHub, except perhaps an optional update check).

* **New Relic APIs & SDKs:** The bottom layer is New Relic itself. Our server communicates with New Relic through official channels:

  * Primarily using **NerdGraph (GraphQL API)** for flexible queries – e.g., to retrieve metrics timeseries, to fetch entities by name or tag, and to trigger alert acknowledgments or changes if needed. GraphQL allows requesting exactly the fields we need (minimizing data transfer) and is the recommended way in 2025 to interact with New Relic programmatically.
  * Utilizing **New Relic’s REST endpoints** for any functionality not yet in GraphQL (if any), such as certain alert or account operations. However, the design prefers GraphQL for consistency.
  * Optionally, using a Python SDK or wrapper if available (for example, the `newrelic-sb-sdk` or similar libraries) to handle auth and queries. This can speed up development (these SDKs often provide convenient methods for common tasks), but we remain mindful of adding dependencies. Even without an SDK, the implementation will be straightforward requests to New Relic’s API endpoints with the appropriate API keys.
  * **Authentication:** All calls to New Relic require API keys (User API key or Insights Query key depending on the API). These keys are stored in the server’s environment or config securely, never exposed to the client side. The design might support multiple key types if needed (for different New Relic APIs), but generally one high-privilege read API key per account is sufficient.

The overall flow is: an AI agent (Claude or Copilot) issues a request in natural language, the AI’s MCP client translates that into a **tool invocation** to our server (e.g., calling `get_apm_metrics` with certain arguments). The server executes the function, which fetches data from New Relic, possibly references the entity definition data for context, and returns a result. The result is serialized (e.g. to JSON or a formatted string) and sent back through MCP to the AI, which can then incorporate it into its response to the user. Throughout this process, the AI doesn’t directly call New Relic – it only sees the abstracted tool interface and results, ensuring a secure separation.

## Directory Structure

We will organize the project repository for clarity, modularity, and ease of extension. A proposed directory structure is as follows:

```
mcp_newrelic/
├── server.py             # Entry-point for the MCP server (initializes FastMCP and registers modules)
├── config.py             # Configuration handling (loading env vars, etc.)
├── cli.py                # CLI tool entry (for direct usage and account switching)
├── modules/              # Package for feature modules, each exposing a set of tools
│   ├── __init__.py
│   ├── apm.py            # APM Module: tools for application performance metrics
│   ├── alerts.py         # Alerts/Incidents Module: tools for alerts, violations, incidents
│   ├── entities.py       # Entities Module: tools for entity inventory and relationships
│   ├── metrics.py        # Metrics/NRQL Module: tools for generic queries and golden metrics
│   └── ... (future modules, e.g., logs.py, synthetics.py)
├── data/
│   ├── entity_definitions/   # Cached entity definition files (could be submodule or downloaded data)
│   └── ... (other static data or sample responses)
├── tests/                # Test cases for each module’s tools
├── requirements.txt      # Dependencies (FastMCP, any NR SDK, etc.)
└── README.md             # Documentation for setup and usage
```

**Key Points of this structure:**

* Each functional domain has its own module in `modules/`. Inside, we define functions decorated with `@mcp.tool` (and possibly `@mcp.resource` for read-only data context) to register them with the server. For example, `modules/alerts.py` might look like:

  ```python
  from fastmcp import mcp  # our FastMCP instance initialized in server.py

  @mcp.tool  
  def list_recent_incidents(hours: int = 24) -> List[Incident]:
      """Fetch incidents opened in the last N hours from New Relic."""
      # (implementation that queries New Relic GraphQL)
      return incidents_list

  @mcp.tool  
  def acknowledge_incident(incident_id: str) -> str:
      """Acknowledge an incident by ID."""
      # (implementation calling NR API to acknowledge)
      return f"Incident {incident_id} acknowledged."
  ```

  Splitting into modules ensures **feature separation of concerns**. It also means new features (like a `logs` module) can be added without touching core logic, simply by creating a new module and importing it in `server.py` to register its tools.

* The **server.py** is responsible for creating the FastMCP server instance and loading all modules. For instance:

  ```python
  from fastmcp import FastMCP
  mcp = FastMCP(name="NewRelicMCP", instructions="...")  # instructions can describe usage
  # Import modules to register tools
  import modules.apm
  import modules.alerts
  import modules.entities
  import modules.metrics

  if __name__ == "__main__":
      mcp.run()
  ```

  We pass a human-readable name and optional instructions (system prompt for the AI describing what the server can do). FastMCP will automatically gather all decorated tools and resources as part of the server. This design makes it easy to **compose** the server from many small pieces. FastMCP also ensures that duplicate registrations are handled according to settings (we can configure `on_duplicate_tools` to “error” to avoid accidental name conflicts).

* **Configuration management** is encapsulated in `config.py`. This module will read environment variables (like `NEWRELIC_API_KEY`, `NEWRELIC_ACCOUNT_ID`, etc.) and provide them to modules that need them (e.g., a function to get the GraphQL endpoint and headers). We use environment variables (with an optional `.env` file for development) to allow easy account switching without code changes. For example, a user can set `NEWRELIC_ACCOUNT_ID` to switch context, or run the server with different env for each account. If multiple configurations need to be stored, we could also support a config file approach (like a YAML with profiles for different accounts).

* The **CLI utility** (described in detail below) is implemented in `cli.py` and possibly installed as an entry point (so the user can run `nr-mcp` from the terminal). This CLI will leverage the same modules, calling the tool functions directly or via an MCP client, to produce output to the console.

* `data/entity_definitions/` will contain the schema of New Relic entities (possibly as YAML files mirrored from the GitHub repo). We might include a script to update these. At runtime, modules like `entities.py` can load this data to know, for example, that a “PIHOLE” entity’s golden metrics are X, Y, Z. Because this data is mostly static, we can load it once at server start (or lazily on first request) and cache it. This avoids repeated GitHub calls and ensures offline capability.

* The structure separates tests, docs, etc. We will include tests for each tool function (these could use stubbed New Relic API responses or a testing mode). Given FastMCP’s built-in testing utilities and possibly a **“dry-run” mode** for tools, we can validate that each tool behaves as expected. This is crucial for maintenance as the New Relic API evolves or as we add new features.

Overall, this structure is designed for clarity: developers can navigate by feature area, and the boundaries between core MCP logic and New Relic-specific logic are clear. It also aligns with FastMCP’s patterns for organizing larger applications (similar to how one would organize a web app by feature).

## Core Modules and Features

This section details the core modules of the MCP server and the features they provide. Each module corresponds to a grouping of related New Relic functionality and encapsulates one or more MCP **tools** (functions accessible to the AI) and possibly **resources** (read-only context data).

### 1. APM Module (Application Performance Monitoring)

**Purpose:** Provide real-time performance data about applications and services monitored by New Relic APM. This includes metrics such as throughput (requests per minute), response times, error rates, Apdex score, and more.

**Key Tools:**

* `get_service_metrics(service_name: str, period: str = "5 minutes") -> dict`: Retrieves key performance metrics for a given service/application over a recent time window (default 5 min). It might return a dictionary of metric names to values (e.g. `{"throughput": 120 req/min, "error_rate": 0.2%, "response_time": 210 ms, ...}`).
* `compare_release_metrics(service_name: str, deployment_id: str) -> str`: Fetches metrics before vs. after a specific deployment (if deployment markers are available in New Relic). This could help with quick regression detection; it might query a timeframe around the deployment and return a textual summary of differences.
* `get_transaction_trace(service_name: str, trace_id: str) -> Resource`: Possibly provide a **resource** (read-only data) for a specific transaction trace or a summary of the slowest transactions. Large data (like full trace details) might be better as a resource that the AI can request to see if needed.

**Implementation Notes:** This module will use New Relic’s APM GraphQL queries (via NerdGraph) to fetch metric timeseries and calculate aggregates. It may also rely on the entity GUID of the service: first resolve the entity by name (or accept GUID directly), then query metrics by that GUID. The **golden metrics definitions** from the entity repo will inform which metrics are most important for a given service type. For example, if the service is a `APM_APPLICATION` type, we know golden metrics include throughput, response time, error rate – the tool can focus on those unless asked otherwise.

This module ensures that if multiple services share a name (common in large accounts), we handle it (maybe requiring a unique identifier or letting the AI clarify). Output is formatted for readability since these results often end up in a chat – e.g., rounding values and adding units (ms, RPM, etc.) for clarity.

### 2. Alerts & Incidents Module

**Purpose:** Allow querying and managing New Relic alerts and incidents. This helps AI agents summarize system issues and potentially assist in incident response workflows.

**Key Tools:**

* `list_recent_incidents(status: str = "open", limit: int = 5) -> List[Incident]`: Returns recent incidents, filtered by status (open, closed) and limited to a number. Each incident could include fields like id, title, triggeredAt, affectedEntities, currentState. This gives an at-a-glance view of ongoing problems. For example, Claude could call this to answer “Are there any ongoing incidents right now?” and then summarize each incident’s details.
* `get_incident_details(incident_id: str) -> str`: Returns a detailed human-readable summary of a specific incident, including what triggered it (violation description), which entities are affected, and links to relevant charts (if any). This tool would gather data from New Relic’s Incident GraphQL (or REST) API.
* `acknowledge_incident(incident_id: str) -> str`: (If read/write operations are allowed) Acknowledge an incident or close an alert condition. This tool would perform a state change via API. Because this is potentially sensitive (it changes system state), we design it to only be used with explicit user instruction/confirmation. The AI should ideally ask the user to confirm before calling it, per OpenAI/Anthropic guidelines for agents. We might mark it in the tool description as requiring confirmation.
* `list_alert_policies() -> List[str]`: Lists names of alert policies or conditions configured, which could help AI answer questions about what thresholds exist (though detailed policy querying might be too granular for our purposes).
* `get_alert_history(entity_name: str, days: int = 1) -> str`: Summarizes any alerts/violations that involved a given entity in the past N days. This would require querying events or alert logs for that entity.

**Implementation Notes:** This module will primarily use New Relic’s **AI incidents API** (GraphQL `actor.incidents` fields) to fetch incidents and their associated alerts. For alert policy info, we might use the NerdGraph `alerts` schema or fallback to REST endpoints (New Relic has REST APIs for Alerts). We’ll use the account context (account ID in queries) to ensure we only fetch incidents for the current account.

Formatting is key – incidents might contain Markdown or long descriptions. We might strip or truncate to keep responses concise for AI consumption. Also, any IDs that the AI might need to reference (like incident IDs) will be kept as short strings in responses so the AI can easily copy them into an acknowledge command if needed.

By providing these tools, an AI like Copilot Chat can not only *detect* that an incident exists (by calling `list_recent_incidents`) but also retrieve deeper info (`get_incident_details`) and even act (`acknowledge_incident`) – enabling a loop of **observing and intervening** under human guidance. This matches the goal of speeding up incident response by giving the AI agent first-class access to observability data.

### 3. Entities & Relationships Module

**Purpose:** Expose the structure of the monitored environment – the inventory of entities (applications, services, hosts, containers, etc.) and how they relate (service maps, dependencies). This gives AI context about the system architecture and enables impact analysis (e.g., “if Database X goes down, what services are affected?”).

**Key Tools:**

* `list_entities(filter_type: str = None) -> List[str]`: Returns a list of entity names (or IDs) in the account, optionally filtered by type (e.g. only “APM\_APPLICATION” or only “HOST”). This is a broad discovery tool.
* `get_entity_info(entity_name_or_id: str) -> str`: Returns detailed info on a specific entity – its type, recent health status, important metrics, and related entities. For example, if called on a service, it might output: *“Service A (GUID 12345, type APM\_APPLICATION) – currently reporting 200 RPM, 0.5% errors. Golden metrics: 99th percentile latency 300ms, etc. Upstream: Service B, Downstream: Database C.”* The upstream/downstream relationships would be fetched via relationship APIs or derived from the entity definitions rules.
* `get_entity_map(entity_name: str, depth: int = 1) -> Resource`: Provides a structured representation (e.g. a JSON or Graphviz dot string) of the entity’s relationship graph up to a certain depth. Depth 1 might show its direct dependencies; depth 2, dependencies-of-dependencies, etc. This could be used by an AI to visualize or to analyze cascading impacts.
* `find_entities_by_tag(tag_key: str, tag_value: str) -> List[str]`: Query entities by tags (since New Relic entities can have metadata tags). This can help an AI filter components, e.g., “find all services tagged environment\:production and team\:payments”.
* `get_topology_overview() -> Resource`: (Potential extension) A resource that provides a high-level system topology or a summary of how many services, hosts, etc., exist – giving context like “10 services, 3 databases, 50 hosts monitored” which an AI might use as background.

**Implementation Notes:** This module leans heavily on New Relic’s **Entity Search and Entity Relationships** APIs. NerdGraph allows searching entities with NRQL-like queries or filters (e.g., by name or tag). For relationships, there is likely a GraphQL field to get related entities (the entity definitions repository defines how relationships are synthesized – for example, an APM service might have a `HAS_DATABASE` relation to a DB entity, etc.).

We’ll integrate the **open-source entity definitions** to enrich this:

* We can decode relationship types from the definitions to present more human-friendly descriptions (e.g., “Service A calls Service B (dependency)” instead of just listing GUIDs).
* The definitions also list which entity types are considered “alertable” – our module can indicate if an entity can have alerts or not.
* Golden tags (if defined) could be mentioned or used for filtering suggestions.

This module effectively provides the **knowledge graph** of the infrastructure to the AI. It must handle possibly large graphs, so tools like `get_entity_map` should be careful with size (maybe limit nodes or depth to avoid info overload in the AI context window). Using resources for larger data (so the AI explicitly requests to see it) can mitigate this.

### 4. Metrics & NRQL Module

**Purpose:** Offer flexible querying of metrics, events, and logs via New Relic’s Query Language (NRQL), as well as easy access to commonly needed metrics such as the golden metrics for any entity type.

**Key Tools:**

* `query_nrql(account_id: int, nrql: str) -> str`: Executes an arbitrary NRQL query and returns the results in a readable format. This is a powerful catch-all – users can ask the AI things beyond the predefined tools, and the AI can formulate an NRQL query to answer it (if it knows NRQL). For example, “What was the maximum CPU utilization of Host X in the last hour?” – the AI could translate that to a NRQL query on the Metric timeslice data. The tool will run the query and perhaps return a small table or summary of the result. We will need to guard this tool to prevent extremely heavy queries or at least document that complex queries might be slow.
* `get_golden_metrics(entity_name: str) -> str`: As described earlier, fetches the golden metrics for the specified entity and returns a summary. It uses the entity definitions to identify the golden metrics keys, then queries their latest values via the Metric API. This is extremely useful for quick health checks. For example, if the user asks “How is my Redis cache doing?”, Claude can call `get_golden_metrics("Redis Cache")` and respond with, “Cache XYZ – throughput 500 ops/sec, latency 2ms, CPU 75% (all within normal ranges).”.
* `chart_metric(entity_name: str, metric_name: str, since: str = "30 min") -> Resource`: Generates a simple text-based chart or summary of a metric over a timeframe. This could output, for instance, a Sparkline or just min/avg/max values. While visual charts in pure text are limited, even a list of timestamped values or a tiny bar chart could be helpful. In future, this might even render an image URL for a chart (if the client UI can display it). This is optional but nice-to-have for analysis.
* `get_anomalies(entity_name: str) -> str`: (Future extension) If New Relic has an AI anomaly detection or forecast API, this tool could surface any anomalies in metrics for the entity (e.g., sudden spike detected in error rate). Since the question hints at future “proactive recommendations”, an anomaly detection integration could be part of that.

**Implementation Notes:** This module uses the **Insights query API** (NRQL). We will parse the NRQL result JSON and format it. Often NRQL results might be a list of result rows (for SELECT statements) – if so, we’ll format them as a table or bullet list for easy reading. For timeseries queries (SELECT time series), we might aggregate or pick out interesting points (like latest value and trend). The design should ensure that the output is concise by default, to fit in AI context, but can be expanded if needed (perhaps via a resource or a follow-up call to get raw data).

We’ll likely impose some limits: e.g., restrict the `nrql` tool to only the current account (making the account\_id optional or fixed), and maybe reject queries that attempt to mutate (NRQL is read-only though). Also, since NRQL can query logs, events, etc., this one tool covers logs querying if needed (though if logs are a big use-case, a separate logs module with structured queries might be better).

Combining with LLM capabilities: an AI like Copilot might generate the NRQL string from natural language and use this tool, which is powerful. To help, we can provide *resource documents* (static context) with examples of NRQL queries or the schema (like a cheat sheet of NRQL usage). This would be an example of MCP **resources** usage – e.g., a `NRQL_CheatSheet.txt` resource that the AI can load if it’s unsure how to form a query. FastMCP supports providing such static resources easily.

### 5. Other Potential Modules

The design allows adding modules as needed:

* **Logs Module:** Tools to query New Relic Logs (if enabled for the account) with specific filters (could reuse `query_nrql` under the hood with `FROM Log` queries).
* **Synthetics Module:** Tools to check status of synthetic monitors, or trigger them.
* **Deployment Module:** If integrating with deployment markers or CI/CD, tools to note when code changes happened relative to metrics (some of this overlaps with APM module).
* **User-defined Extensions:** Because the system is modular, users could plug in their own tools. For instance, if a user wants a custom action like clearing a cache via an API call, they could add a new tool function. (This might be outside the core scope, but it’s possible due to FastMCP’s flexible design.)

Each module registers its tools such that they are **self-describing** to the AI agent. MCP includes a mechanism for the client to fetch the schema or description of tools (their name, params, and docstring) via the `list_tools` request. FastMCP handles a lot of this automatically, leveraging Python type hints and docstrings to inform the LLM of usage. We will write clear docstrings for each tool so that AI agents understand their purpose and parameters. For example, the docstring for `query_nrql` will mention the expected NRQL syntax and maybe an example. This is crucial for **discoverability**, enabling the AI to decide which tool to use without human prompting.

## Entity Definitions Integration

One standout feature of this design is the integration of **New Relic’s open-source entity definitions** for golden metrics and metadata. Here’s how we will use these definitions:

* **Golden Metrics Reference:** The repository provides YAML files specifying *golden metrics* for each entity type (e.g., a `WebService` might have `response.time`, `throughput`, etc. marked as golden). We will parse these files at startup (or build time) and create a dictionary mapping entity type -> list of golden metric names (and possibly units). Our `get_golden_metrics` and `get_entity_info` tools then leverage this map. This ensures the server always knows which metrics to highlight. If the definitions update (say New Relic adds a new golden metric for a Kubernetes node), updating the data file is all that’s needed to reflect that in our tool outputs.

* **Entity Metadata:** The definitions include descriptions of entity types, lifecycle (alertable or not), and summary metrics. We can use these to make the AI’s responses richer. For example, if an entity type has a description in the repo (“a PIHOLE is a DNS sinkhole device…”), the `get_entity_info` tool might include a one-liner from that to clarify what that entity is. This is especially helpful for less common entity types or custom ones contributed via this repo.

* **Relationship Synthesis:** The repository’s experimental features include **relationship synthesis rules**, which define how entities relate (for example, an APM Application might *HAS\_A* relationship to a Mobile app or *DEPENDS\_ON* a Database if certain telemetry is present). While our server can also directly query relationships from New Relic GraphQL, having the rules means we can infer relationships that might not yet be realized or easily queryable. We could, for instance, implement a logic that if an APM service and a database have matching tags or instrumentation links per the definitions, we know there’s a dependency.

* **Continuous Updates:** To keep things future-proof, we will automate pulling updates from the `newrelic/entity-definitions` repo (maybe pin to a certain release and allow manual updates for stability). This could be via a git submodule or a small script that fetches the raw GitHub content periodically. We will document how to update these definitions so maintenance teams can refresh the data as New Relic evolves (e.g., new entity types for new services).

* **Open-Source Collaboration:** Because this repo is open to contributions, if our MCP server identifies an issue or an improvement (for example, if we build a new entity type for a custom integration and want golden metrics for it), we can contribute back. This isn’t directly part of our server’s operation, but it’s a note that our design aligns with the community-driven model of entity definitions.

In practice, the integration might involve loading a YAML like:

```yaml
# Example snippet of golden_metrics.yml
APM_APPLICATION:
  golden_metrics:
    - metric: apm.service.transaction.duration
      summary_function: average
      unit: milliseconds
      name: Response Time (avg)
    - metric: apm.service.error.rate
      summary_function: average
      unit: percent
      name: Error Rate (avg)
    ...
```

Our server code would transform that into a Python dict:

```python
GOLDEN_METRICS['APM_APPLICATION'] = [
    {"metric": "apm.service.transaction.duration", "name": "Response Time", "unit": "ms"},
    {"metric": "apm.service.error.rate", "name": "Error Rate", "unit": "%"},
    ...
]
```

And then `get_golden_metrics(entity)` would find the entity’s type (via a GraphQL query `entity.guid` -> type name), look up the list, and then query the latest values of those metric keys from New Relic. The result might be a nicely formatted block the AI can present.

By grounding our server in these definitions, we ensure **consistency** with New Relic’s own UI and terminology. It also **future-proofs** the server to some extent – as new “golden” practices emerge, updating the definitions keeps the MCP server in sync without code changes.

Finally, note that these definitions also cover **Summary Metrics** (a small set of metrics shown in entity explorer) and **Golden Tags** (important tags). If needed, we could have tools that leverage those (for example, a tool to list golden tags which might highlight key attributes like environment or team owner). At minimum, we’ll focus on golden metrics and relationships as core value adds.

## CLI Utility Design

In addition to AI-driven chat usage, we will provide a **command-line interface (CLI)** for direct human operation and scripting. The CLI serves two main purposes:

1. Allow engineers to quickly invoke the same tools for debugging/troubleshooting via terminal.
2. Provide a mechanism to switch configuration (account context) or manage the server.

We’ll likely create an installable console script (using `setuptools` entry\_points or similar) named, for example, `nr-mcp`.

**CLI Modes and Commands:**

* **Interactive Mode:** If the user runs `nr-mcp` with no arguments (or with a special flag), we can drop into an interactive REPL where one can type commands corresponding to tools. This is akin to a text-based chat with the server but without the LLM in between. For example:

  ```
  $ nr-mcp
  New Relic MCP CLI – type 'help' for commands.
  nr-mcp> list_recent_incidents --hours 2
  [Incidents]
  - INC-001234: High Error Rate on Service Foo (open since 2025-06-07 10:00 UTC)
  - INC-001235: Memory spike on Host Bar (open since 2025-06-07 09:30 UTC)
  nr-mcp> get_entity_info "Service Foo"
  Service Foo (APM Application GUID …) – Web service owned by Team X.
  Performance: 120 req/min, 0.5% errors (normal), Resp time avg 210ms.
  Dependencies: -> Database Y, -> 3 External Services.
  ...
  nr-mcp> exit
  ```

  This interactive mode is a nice-to-have for those who prefer direct control or for quick tests of the server’s capabilities. It essentially wraps calls to the tool functions and pretty-prints results.

* **Direct Commands:** The CLI will also support one-shot commands for scripting. For instance:

  ```
  $ nr-mcp query_nrql "SELECT average(cpuPercent) FROM SystemSample WHERE hostname = 'host123' SINCE 30 minutes ago"
  ```

  would output the results and exit. This makes it easy to integrate with other scripts or cron jobs. We’ll parse arguments and route them to the corresponding tool. Using a library like `argparse` or `click` can help define commands for each tool, including help text derived from the tool’s docstring.

* **Configuration Commands:** We plan to allow easy switching of account or environment via CLI. If multiple New Relic accounts need to be accessed, the CLI could offer:

  * `nr-mcp config list` to list saved profiles (if we implement profiles in a config file).
  * `nr-mcp config use <profile>` to switch the environment variables or context to that profile.

  Alternatively, simply setting environment and running might be enough (one could script `NEWRELIC_ACCOUNT_ID=ABC NEWRELIC_API_KEY=XYZ nr-mcp ...`). For user convenience, a simple `nr-mcp switch-account <ID>` could reload the server with new credentials (if the server supports hot-reloading config). In practice, it might just print instructions to restart with new env, unless we decide to dynamically allow multiple accounts (not in current scope).

* **Server Management:** Basic controls like `nr-mcp start` and `nr-mcp stop` might be included if we run the server as a background daemon. However, since FastMCP’s CLI (`fastmcp run`) already can run the server, we might integrate or wrap that. The FastMCP CLI provides `fastmcp run`, `fastmcp dev`, etc., but our `nr-mcp` could call `mcp.run()` internally anyway. We will ensure that running `nr-mcp` starts the server with the appropriate mode (STDIO vs HTTP) as needed.

**Using FastMCP CLI Capabilities:** Notably, FastMCP itself comes with CLI support – for example, one can do `fastmcp run server.py`. It also has a `fastmcp dev` mode that launches an inspector UI for testing tools, and an `install` command for Claude Desktop integration. We can leverage these under the hood:

* For instance, `nr-mcp install` could effectively run `fastmcp install` to register the server with Claude Desktop (this might package it or create a shortcut that Claude Desktop can use to spawn it).
* `nr-mcp dev` could run in a special mode that starts the server and opens a testing interface (which might display logs and allow manual tool invocation via a web UI). This is useful for development and troubleshooting our server itself.

We will document these CLI commands in the README, so users know they have both AI-driven and direct control options. The CLI is also critical for **automation** – e.g., a Jenkins pipeline could call `nr-mcp get_golden_metrics "Service Foo"` after a deployment and decide whether to promote based on the output.

In terms of implementation, using a library like `click` can elegantly define subcommands corresponding to each tool, using the tool’s function name and parameters. We might auto-generate some of this to avoid duplicating definitions (since tools are already defined with names and type hints). Another approach is to instantiate a local `Client(FastMCPTransport)` to call our server in-process for each command, which actually executes the same path as an external call (ensuring parity between CLI and AI usage). FastMCPTransport allows an in-memory call to the server without HTTP, which is perfect for CLI – no overhead of network serialization.

**Example CLI implementation snippet:**

```python
import click
from mcp_newrelic import server  # ensures FastMCP server and tools are loaded

# Suppose server.mcp is the FastMCP instance
client = server.mcp.client()  # creates a local client connected to the same process via FastMCPTransport

@click.group()
def cli():
    """New Relic MCP CLI - directly invoke tools or manage config."""
    pass

@cli.command()
@click.argument('nrql_query', type=str)
def query_nrql(nrql_query):
    """Run an arbitrary NRQL query on the current New Relic account."""
    result = client.query_nrql(nrql_query)  # calls the tool
    click.echo(result)

# ... similarly for other tools ...
```

This approach treats each tool as a subcommand. Alternatively, for brevity, we might have a single command like `tool <tool_name> [args...]` to call any tool generically, but that’s less user-friendly.

In conclusion, the CLI is a valuable addition for usability and testing. It also serves as a fallback if, for instance, an AI is not available – a human can still use the same capabilities directly. Moreover, by using the CLI in CI pipelines or cron jobs, organizations can leverage the work done here beyond just AI interactions (essentially reusing the MCP server as a general New Relic automation tool).

## Configuration and Environment Handling

Configuring the MCP server for different accounts and environments must be straightforward and secure. Here’s our plan for configuration:

* **Environment Variables:** We will use environment variables as the primary means to configure sensitive values and account-specific settings. Key variables include:

  * `NEWRELIC_API_KEY` (or more specifically `NEWRELIC_USER_API_KEY` for GraphQL, and maybe `NEWRELIC_INSIGHTS_KEY` if needed for querying Insights – though one key can often suffice for all).
  * `NEWRELIC_ACCOUNT_ID` to scope certain queries if needed.
  * Other optional keys: e.g., `NEWRELIC_REGION` if using EU vs US (for API endpoints), or toggles like `NEWRELIC_VERBOSE_LOGGING`.

  FastMCP’s server settings can also be set via env (prefixed `FASTMCP_SERVER_...` as per FastMCP documentation). For example, to change the default port or host for the server’s HTTP mode, one could set `FASTMCP_SERVER_PORT=8080` or similar. We will expose these in documentation.

* **Configuration File:** In addition to env vars, we may support a simple config file (YAML or JSON). For instance, a `config.yml` could allow specifying multiple profiles:

  ```yaml
  profiles:
    prod:
      newrelic_account: 12345
      newrelic_api_key: NRAK-XXXX...
    staging:
      newrelic_account: 67890
      newrelic_api_key: NRAK-YYYY...
  active_profile: prod
  ```

  The server on startup can read this and apply the active profile (overriding environment if present). This is useful if running the server as a long-lived service that may need to switch contexts occasionally without restarting the container with new env vars. However, since the requirement is one account at a time, switching will likely involve a restart or at least a fresh instantiation of the server.

* **Runtime Switching:** If truly needed, we could implement an MCP **tool** for switching account context at runtime (e.g., a tool `use_account(profile_name)` that causes the server to reload config for a different account). This might be tricky (resetting global state, flushing caches, etc.), and could confuse an AI mid-conversation. It’s probably safer to treat account switching as a deployment-time concern (i.e., run separate instances for each account, or restart with different config). So our design will *allow* easy switching (via config/env changes) but not necessarily *hot-swap* without restart.

* **Security:** All secrets (API keys) are kept in memory on the server side. We will **never** log the API key or expose it in responses. If the AI tries to get the server to reveal the key (it should not have a tool for that, and even if it tried to call some lower-level function, it wouldn’t succeed because that’s outside the tool interface), the protocol design prevents it. The only way secrets are used is to authenticate with New Relic’s backend on server-side HTTP calls.

* **Validation of Config:** On startup, the server can perform a quick self-check: e.g., validate that the API key works by fetching the current user or account name (using a cheap GraphQL query like `{actor { user { email } }}`). This way, if keys are misconfigured, it can log a clear error early. It can also check that the entity definitions data is present and up-to-date (logging a warning if not).

* **Multiple Instances vs Multi-tenancy:** If multiple accounts need to be used concurrently (like servicing multiple users each with their own New Relic account), our design would lean towards running separate instances for each account (each with its own config). This isolation is simpler and avoids multi-tenant complexity. There is work in the community on multi-tenant MCP servers (e.g., a Vercel serverless approach that dynamically routes to different backends based on user context), but that’s beyond our scope here. For now, one process = one account context, but switching that context is as simple as providing new credentials and restarting the process.

* **Deployment Config:** We will ensure that configuration via environment is compatible with deployment to containers or cloud platforms. For example, if deploying on Kubernetes, one would use a Secret for the API key and an EnvVar for the account ID. Our app will read those on launch. We won’t hardcode any file paths or OS-specific config, making it portable.

In summary, **configuration** is kept flexible but explicit. The use of environment variables aligns with 12-factor app principles and allows secure injection of secrets. By limiting to one account at a time, we avoid any risk of cross-account data leakage and keep the logic straightforward.

Finally, we will provide **documentation** (in README or a docs section) listing all env vars and config options, with examples. For instance: *“To run the server for a different New Relic account, set the `NEWRELIC_API_KEY` and `NEWRELIC_ACCOUNT_ID` for that account and restart the server. If using Docker, you can pass these as environment variables. If using the CLI, you might create a `.env` file in the working directory.”* This ensures future maintainers or users can easily understand how to point the server to their account.

## Observability and Logging

Building an observability tool without being observable itself would be ironic – so we will implement robust **observability** for the MCP server. This includes logging, metrics, and possibly tracing:

* **Structured Logging:** The server will produce logs for important events: startup, configuration loaded, each tool invocation, errors from external API calls, etc. We’ll use Python’s logging library configured to output structured logs (e.g., JSON or key-value) so that they can be easily parsed by log aggregators (maybe even sent to New Relic itself!). At minimum, logs will include timestamp, severity, and a message. For tool invocations, we might log an entry like: `INFO ToolCall tool=list_recent_incidents user=ClaudeDesktop account=NR_ACC_123 duration=50ms result_count=2`. We will avoid logging sensitive data (we can log that a query was made, but not necessarily dump all query results unless at debug level).

* **MCP Client-visible Logs:** FastMCP supports sending log messages back to the client LLM for debugging. We can utilize this for certain info – for example, if a tool call fails (say the New Relic API returns an error), we could emit a log that the client (Claude or Copilot) might pick up and could choose to show or use to adjust strategy. However, we must be careful; we don’t want to flood the AI with internal logs unless necessary. Likely, we’ll use client logging mostly at DEBUG level for development or if the user explicitly asks the AI to enable verbose mode.

* **Metrics (Instrumentation):** We will instrument the server to collect metrics about itself, such as:

  * Number of tool calls (per tool, and total).
  * Latency of tool calls (how long each invocation takes).
  * Error rates (how many calls resulted in exceptions or New Relic API errors).
  * Perhaps resource usage (CPU/memory of the server process).

  Since this is a Python service, we can expose these metrics via an endpoint (like an optional `/metrics` HTTP endpoint in Prometheus format) or even push them to an external system. Given we are dealing with New Relic, one idea is to use New Relic’s own telemetry SDK to send the MCP server’s metrics to New Relic as a “custom application” – essentially dogfooding the observability. This would allow us to monitor the MCP server in New Relic APM (seeing its performance, memory, etc., as a side benefit). However, integrating the full New Relic agent might be heavy; a simpler way is to expose Prometheus metrics and let a sidecar scrape them.

  Nonetheless, for the scope here, at least an internal metrics registry (maybe using Python’s `prometheus_client`) will be set up. We’ll track metrics like `mcp_tool_invocations_total{tool="list_recent_incidents"}`. These can help in debugging and scaling (e.g., if one tool is used extremely frequently, maybe we need caching on it).

* **Tracing:** If we integrate OpenTelemetry, we can have traces for each tool execution, with spans for “New Relic API call”, etc. This might be overkill now, but could be a future addition – especially if diagnosing performance issues in the MCP server. At minimum, we will include correlation IDs in logs for requests. MCP itself likely assigns an ID for each request; we can echo that in logs to correlate a request’s multiple log lines.

* **Error Handling & Alerts:** We will handle exceptions in tool execution gracefully, returning error messages to the AI and logging stack traces to our logs. Additionally, if certain errors happen (like authentication failure from New Relic API, or a too-slow query), we might trigger an internal alert. For example, if we integrate with New Relic (again, dogfooding), we could have an alert policy on “MCP Server error rate” so that the maintainers are notified if the MCP server itself is failing often.

* **Observability of MCP interactions:** We might want to log which client is calling (Claude vs Copilot vs CLI). This can be determined by context (Claude Desktop STDIO vs an HTTP user agent string from VS Code, etc.). We can tag logs/metrics accordingly, which is helpful for usage statistics (e.g., 70% of calls come from Copilot vs 30% from Claude – interesting insight!).

* **Testing & Monitoring:** We will likely run the MCP server in a staging mode with synthetic tests (maybe a cronjob that calls a couple of tools and verifies responses). This ensures everything is working and also generates baseline load/metrics we can observe.

By building strong observability in, we ensure that as the MCP server scales to more users or if something goes wrong (like New Relic API changes), we can quickly identify the issue.

In terms of best practices (2025 state-of-the-art):

* We will use **OpenTelemetry** SDK for Python to instrument HTTP calls to New Relic – tagging spans with the API endpoint and response time. If an org is using distributed tracing, this could integrate with their systems.
* Logging will possibly be done through a modern logging framework that supports structured logs out of the box (like structlog, or Python’s logging with a JSON formatter).
* We’ll consider performance impact of logging; use async logging if needed to not block tool execution.

To sum up, this MCP server will itself be monitored as a first-class citizen, and we can even use it to monitor itself (since it can send logs or metrics to New Relic!). This reflexive use is quite powerful: one could ask the MCP (if allowed) “How many times has this server been used today?” and if we exposed that info via a tool, it could answer using its own metrics.

## Deployment and Extensibility

**Deployment:** The MCP server is designed to be lightweight and deployable in various environments:

* We can containerize it with a Dockerfile that simply installs the Python dependencies and runs `server.py`. Since it’s a standalone service, running it in a container orchestrator or as a simple process on a VM is fine. In container form, we might expose port 8000 (default FastMCP HTTP port) for network access to AI clients like VS Code. If only used locally (e.g., with Claude Desktop), users might just run it on their laptop via CLI (no special infra needed).
* For cloud deployment (for sharing among a team or integrating with cloud-based Copilot), we could deploy it to a small VM or Azure Container App, etc. It doesn’t require heavy resources – mostly network I/O bound when querying New Relic. Python’s GIL means single-threaded by default, but FastMCP likely uses async IO under the hood for concurrency. We can scale by running multiple instances if needed (behind a load balancer, if serving many simultaneous requests from different AI clients).
* We’ll ensure the container or app can be configured via environment (as mentioned). Secrets can be mounted from a secure store (Kubernetes secret, AWS Parameter Store, etc.).

**Scaling:** In early stages, one instance should handle typical usage (the volume of requests is tied to how often the AI chooses to call tools – which in a chat session might be a few per user question). If we need to scale:

* **Horizontal scaling** is straightforward: the server is stateless (no session persistence except maybe in-memory caches, which can be safely duplicated). We can run multiple replicas and, if using HTTP, put them behind a load balancer. GitHub Copilot’s config could point to a load balancer URL. Claude’s STDIO mode is one-to-one with a local process, so scaling doesn’t apply there (each user has their own instance in that case).
* **Caching layer:** To reduce load on New Relic APIs, we can introduce caching for frequent queries. For example, if `get_golden_metrics` is called repeatedly for the same entity within a short window, we can cache those metric values for a minute. Similarly, `list_entities` results can be cached for some time. This improves performance and avoids hitting rate limits. We will need to be mindful of cache invalidation (for dynamic data like incidents, a short cache TTL or no cache is better).
* **Rate Limiting:** The server should also protect New Relic from being overwhelmed. If an AI or user script loops a heavy query, we might implement an internal rate limit (e.g., no more than X NRQL queries per minute). New Relic’s APIs have their own limits; we should handle HTTP 429 responses gracefully (maybe informing the AI to back off). We could even expose a resource like `rate_limits` so the AI can be aware of how many calls it can make (though that might be overkill).
* **Maintenance:** Upgrading the server (e.g., to support new tools or New Relic API changes) should be done carefully – since AI might rely on certain tool names and behaviors, we maintain backward compatibility when possible. If we must change a tool interface, we should version the API or add new tools rather than break existing ones, because AI models might have been trained/fine-tuned on the older schema.
* **Monitoring Deployment:** Using the observability features, we will monitor how the server performs in production. If CPU or memory is high, we may allocate more resources or optimize code (e.g., using async where blocking). If certain tools are slow, maybe add concurrency or optimize those specific queries.

**Extensibility & Future Extensions:**

The design is intentionally extensible. Some possible future improvements and how we can accommodate them:

* **Guided Root Cause Analysis (RCA):** We could integrate an AI logic that correlates data to guess at root causes. For instance, a future extension might use the metrics and incidents data to do a causal analysis (perhaps leveraging an internal library or a service). Our MCP server could expose a high-level tool like `diagnose_issue(entity_name)` which under the hood calls multiple other tools (metrics, incidents, logs) and applies an algorithm to suggest a probable cause (e.g., “High CPU on Service A coincided with a deployment and a cache miss surge, likely cause: new deployment introduced caching issue”). This is speculative, but the architecture would allow it – it could be another module that orchestrates calls or uses a local ML model. Because MCP tools can call code, we have full flexibility to implement such logic.

* **Proactive Recommendations:** Similar to RCA, we might add tools that proactively scan for anomalies or inefficiencies (like “find any service with error rate above 5% in last 1h”). The AI could call this periodically or when asked “Any problems I should be aware of?”. Implementing this might involve background threads or on-demand checks across multiple entities. We’d consider performance (maybe not scanning everything on the fly unless user asks).

* **Support for Other Observability Platforms:** The modular design can be generalizable to other systems like Datadog, Splunk, Prometheus, etc. We could either:

  * Extend this server to have modules for other platforms if we want a unified “Observability MCP”. That would mean our server could connect to, say, Datadog APIs if configured. This introduces complexity (multi-platform in one). Alternatively,
  * Build separate MCP servers for each platform using a similar pattern. Since our design heavily borrows from New Relic specifics, a different server might be cleaner for another platform. But code reuse is possible; we might abstract common patterns (like a base class for “ObservabilityTool” that handles generic things).

  In any case, by keeping things loosely coupled, adding another platform’s support is a matter of adding new modules and perhaps config for that platform’s credentials. The FastMCP framework even allows composing servers, so theoretically a “master” server could import our NewRelic server and another server (like Datadog server) as sub-components – then an AI client sees tools from both.

* **Collaboration and Community:** By 2025, there is an ecosystem of MCP servers (the search results show many – for logs, for custom things). We should ensure our design can integrate improvements from the community. Maybe someone writes a great `analyze_deployment_impact` tool – we could incorporate that. Using open standards (MCP) and being open about our tool schema allows such collaboration.

* **AI Model Evolutions:** If future AI models support more advanced function calling or native integration (like OpenAI plugins or so), our server can easily be wrapped as a plugin (since it’s essentially an API with an OpenAPI spec via MCP). FastMCP even has OpenAPI integration to auto-generate endpoints. We can use that to expose a REST interface to tools for non-MCP use (for example, an HTTP endpoint for each tool, which could be used by non-MCP clients). This is another form of extensibility – making the service usable beyond MCP if needed.

**Maintenance considerations:**

* We will pin specific versions of dependencies (FastMCP, etc.) to ensure stability.
* Regularly update the New Relic API version usage (GraphQL sometimes introduces new fields, deprecates old ones – keep an eye via their changelogs).
* Keep the entity definitions up-to-date (maybe schedule a quarterly update unless critical).
* Document the code well so new contributors (or internal team members) can add new tools or fix issues easily. Especially document the mapping between New Relic concepts and our modules.

In summary, the deployment is straightforward and the design is built to grow. By leveraging modern frameworks and modular structure, we have a solution that is **future-proof** and can scale with both usage load and expanding feature demands. This MCP server will significantly enhance how AI assistants interact with New Relic, making DevOps and SRE workflows more intelligent and efficient.

**Sources:**

* Anthropic Claude and MCP Integration – STDIO and Tools
* GitHub Copilot Agent (VS Code) and MCP Preview
* FastMCP Framework Overview and Usage
* New Relic Entity Definitions (Golden Metrics, Relationships)
* Example New Relic MCP Server features for reference
* FastMCP Server Configuration and CLI details
