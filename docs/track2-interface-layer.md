# Track 2: Interface Layer - Ultra Detailed Implementation

## Overview
The Interface Layer provides multiple ways to interact with the UDS core: MCP server for AI agents (Copilot/Claude), REST API for applications, CLI for developers, and SSE for real-time streaming. This track creates the "front door" to all UDS capabilities.

## Architecture

```go
// pkg/interface/architecture.go
package interface

/*
Interface Layer Architecture:

┌─────────────────────────────────────────────────────────────────┐
│                        Interface Layer                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │  MCP Server  │  │  REST API    │  │    CLI Tool           │ │
│  │              │  │              │  │                       │ │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌─────────────────┐ │ │
│  │ │JSON-RPC  │ │  │ │ OpenAPI  │ │  │ │ Cobra Commands  │ │ │
│  │ │Handler   │ │  │ │ Handler  │ │  │ │                 │ │ │
│  │ └──────────┘ │  │ └──────────┘ │  │ └─────────────────┘ │ │
│  │              │  │              │  │                       │ │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌─────────────────┐ │ │
│  │ │Tool      │ │  │ │ Router   │ │  │ │ Interactive     │ │ │
│  │ │Registry  │ │  │ │          │ │  │ │ Mode            │ │ │
│  │ └──────────┘ │  │ └──────────┘ │  │ └─────────────────┘ │ │
│  └──────────────┘  └──────────────┘  └───────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Shared Components                         ││
│  │  ┌────────────┐  ┌─────────────┐  ┌──────────────────────┐││
│  │  │ SSE Stream │  │ Auth/Rate   │  │ Request/Response     │││
│  │  │ Manager    │  │ Limiter     │  │ Transformer          │││
│  │  └────────────┘  └─────────────┘  └──────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                 Core Integration Layer                       ││
│  │  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐ ││
│  │  │ Discovery    │  │ Pattern       │  │ Dashboard       │ ││
│  │  │ Adapter      │  │ Adapter       │  │ Adapter         │ ││
│  │  └──────────────┘  └───────────────┘  └─────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
*/
```

## Week 1: MCP Server Implementation

### Day 1-2: MCP Core Infrastructure

```go
// pkg/mcp/server.go
package mcp

import (
    "context"
    "encoding/json"
    "fmt"
    "io"
    "os"
    
    "github.com/uds/pkg/discovery"
    "github.com/uds/pkg/patterns"
)

// MCP Server implements the Model Context Protocol
type Server struct {
    // Core services (interfaces only in week 1)
    discovery  discovery.DiscoveryEngine
    patterns   patterns.PatternEngine
    query      query.QueryGenerator
    dashboard  dashboard.DashboardBuilder
    
    // MCP components
    transport  Transport
    tools      *ToolRegistry
    sessions   *SessionManager
    
    // Configuration
    config     ServerConfig
    logger     *Logger
    metrics    *Metrics
}

// ServerConfig holds MCP server configuration
type ServerConfig struct {
    TransportType   TransportType // stdio, http, sse
    MaxConcurrent   int
    RequestTimeout  time.Duration
    StreamingEnabled bool
    AuthEnabled     bool
}

// Initialize and start the MCP server
func (s *Server) Start(ctx context.Context) error {
    s.logger.Info("Starting MCP server", "transport", s.config.TransportType)
    
    // Register all tools
    s.registerTools()
    
    // Start transport
    switch s.config.TransportType {
    case TransportStdio:
        return s.startStdioTransport(ctx)
    case TransportHTTP:
        return s.startHTTPTransport(ctx)
    case TransportSSE:
        return s.startSSETransport(ctx)
    default:
        return fmt.Errorf("unsupported transport: %s", s.config.TransportType)
    }
}

// Register all available tools
func (s *Server) registerTools() {
    // Discovery tools
    s.tools.Register(Tool{
        Name:        "discovery.list_schemas",
        Description: "List all available schemas in the data source",
        Parameters: ToolParameters{
            Type: "object",
            Properties: map[string]Property{
                "filter": {
                    Type:        "string",
                    Description: "Optional filter for schema names",
                },
                "include_quality": {
                    Type:        "boolean",
                    Description: "Include quality metrics",
                    Default:     false,
                },
            },
        },
        Handler: s.handleListSchemas,
    })
    
    s.tools.Register(Tool{
        Name:        "discovery.profile_attribute",
        Description: "Deep analysis of a specific data attribute",
        Parameters: ToolParameters{
            Type: "object",
            Required: []string{"schema", "attribute"},
            Properties: map[string]Property{
                "schema": {
                    Type:        "string",
                    Description: "Schema/event type name",
                },
                "attribute": {
                    Type:        "string",
                    Description: "Attribute name to profile",
                },
                "sample_size": {
                    Type:        "integer",
                    Description: "Number of samples to analyze",
                    Default:     10000,
                },
            },
        },
        Handler:     s.handleProfileAttribute,
        Streaming:   true, // Supports streaming responses
    })
    
    s.tools.Register(Tool{
        Name:        "discovery.find_relationships",
        Description: "Discover relationships between schemas",
        Parameters: ToolParameters{
            Type: "object",
            Properties: map[string]Property{
                "schemas": {
                    Type:        "array",
                    Description: "List of schemas to analyze",
                    Items:       &Property{Type: "string"},
                },
                "confidence_threshold": {
                    Type:        "number",
                    Description: "Minimum confidence for relationships",
                    Default:     0.7,
                },
            },
        },
        Handler: s.handleFindRelationships,
    })
    
    // Pattern analysis tools
    s.tools.Register(Tool{
        Name:        "analysis.detect_patterns",
        Description: "Detect patterns in data using ML-enhanced analysis",
        Parameters: ToolParameters{
            Type: "object",
            Required: []string{"schema"},
            Properties: map[string]Property{
                "schema": {
                    Type:        "string",
                    Description: "Schema to analyze",
                },
                "attributes": {
                    Type:        "array",
                    Description: "Specific attributes to analyze",
                    Items:       &Property{Type: "string"},
                },
                "pattern_types": {
                    Type:        "array",
                    Description: "Types of patterns to detect",
                    Items:       &Property{Type: "string"},
                    Default:     []string{"all"},
                },
            },
        },
        Handler:   s.handleDetectPatterns,
        Streaming: true,
    })
    
    // Query generation tools
    s.tools.Register(Tool{
        Name:        "query.generate",
        Description: "Generate optimized query from natural language",
        Parameters: ToolParameters{
            Type: "object",
            Required: []string{"intent"},
            Properties: map[string]Property{
                "intent": {
                    Type:        "string",
                    Description: "Natural language query intent",
                },
                "schemas": {
                    Type:        "array",
                    Description: "Schemas to query (auto-detected if not provided)",
                    Items:       &Property{Type: "string"},
                },
                "time_range": {
                    Type:        "string",
                    Description: "Time range for query (e.g., 'last 7 days')",
                    Default:     "last 24 hours",
                },
            },
        },
        Handler: s.handleGenerateQuery,
    })
    
    // Dashboard tools
    s.tools.Register(Tool{
        Name:        "dashboard.create",
        Description: "Create a complete dashboard from requirements",
        Parameters: ToolParameters{
            Type: "object",
            Required: []string{"goal"},
            Properties: map[string]Property{
                "goal": {
                    Type:        "string",
                    Description: "Dashboard goal or requirement",
                },
                "style": {
                    Type:        "string",
                    Description: "Dashboard style (executive, technical, operational)",
                    Default:     "auto",
                },
                "max_widgets": {
                    Type:        "integer",
                    Description: "Maximum number of widgets",
                    Default:     12,
                },
            },
        },
        Handler:   s.handleCreateDashboard,
        Streaming: true, // Stream progress updates
    })
}

// Tool handler implementations
func (s *Server) handleListSchemas(ctx context.Context, params map[string]interface{}) (interface{}, error) {
    // Extract parameters
    filter, _ := params["filter"].(string)
    includeQuality, _ := params["include_quality"].(bool)
    
    // Call discovery engine
    schemas, err := s.discovery.DiscoverSchemas(ctx, discovery.DiscoveryFilter{
        NamePattern: filter,
    })
    
    if err != nil {
        return nil, fmt.Errorf("discovery failed: %w", err)
    }
    
    // Transform response
    response := ListSchemasResponse{
        Schemas: make([]SchemaInfo, len(schemas)),
    }
    
    for i, schema := range schemas {
        info := SchemaInfo{
            Name:          schema.Name,
            AttributeCount: len(schema.Attributes),
            RecordCount:   schema.DataVolume.EstimatedCount,
            LastUpdated:   schema.LastAnalyzedAt,
        }
        
        if includeQuality {
            info.Quality = &QualityInfo{
                Score:  schema.Quality.OverallScore,
                Issues: len(schema.Quality.Issues),
            }
        }
        
        response.Schemas[i] = info
    }
    
    return response, nil
}
```

### Day 3-4: JSON-RPC Protocol Implementation

```go
// pkg/mcp/protocol.go
package mcp

import (
    "context"
    "encoding/json"
    "sync"
    "sync/atomic"
)

// JSON-RPC 2.0 implementation for MCP
type Request struct {
    Jsonrpc string          `json:"jsonrpc"`
    Method  string          `json:"method"`
    Params  json.RawMessage `json:"params,omitempty"`
    ID      interface{}     `json:"id,omitempty"`
}

type Response struct {
    Jsonrpc string      `json:"jsonrpc"`
    Result  interface{} `json:"result,omitempty"`
    Error   *Error      `json:"error,omitempty"`
    ID      interface{} `json:"id"`
}

type Error struct {
    Code    int         `json:"code"`
    Message string      `json:"message"`
    Data    interface{} `json:"data,omitempty"`
}

// Standard JSON-RPC error codes
const (
    ParseError     = -32700
    InvalidRequest = -32600
    MethodNotFound = -32601
    InvalidParams  = -32602
    InternalError  = -32603
)

// Protocol handler
type ProtocolHandler struct {
    server      *Server
    requests    sync.Map // Track in-flight requests
    idCounter   int64
}

func (h *ProtocolHandler) HandleRequest(ctx context.Context, data []byte) ([]byte, error) {
    // Parse request
    var req Request
    if err := json.Unmarshal(data, &req); err != nil {
        return h.errorResponse(nil, ParseError, "Parse error", err)
    }
    
    // Validate JSON-RPC version
    if req.Jsonrpc != "2.0" {
        return h.errorResponse(req.ID, InvalidRequest, "Invalid JSON-RPC version", nil)
    }
    
    // Route to appropriate handler
    switch req.Method {
    case "tools/list":
        return h.handleToolsList(ctx, req)
    case "tools/call":
        return h.handleToolCall(ctx, req)
    case "completion/complete":
        return h.handleCompletion(ctx, req)
    default:
        return h.errorResponse(req.ID, MethodNotFound, "Method not found", nil)
    }
}

// Handle tool invocation
func (h *ProtocolHandler) handleToolCall(ctx context.Context, req Request) ([]byte, error) {
    var params ToolCallParams
    if err := json.Unmarshal(req.Params, &params); err != nil {
        return h.errorResponse(req.ID, InvalidParams, "Invalid parameters", err)
    }
    
    // Get tool from registry
    tool, exists := h.server.tools.Get(params.Name)
    if !exists {
        return h.errorResponse(req.ID, MethodNotFound, "Tool not found", nil)
    }
    
    // Create execution context
    execCtx := &ExecutionContext{
        RequestID: req.ID,
        Tool:      tool,
        StartTime: time.Now(),
    }
    
    // Track request
    h.requests.Store(req.ID, execCtx)
    defer h.requests.Delete(req.ID)
    
    // Handle streaming if supported
    if tool.Streaming && params.Stream {
        return h.handleStreamingToolCall(ctx, execCtx, params)
    }
    
    // Execute tool
    result, err := tool.Handler(ctx, params.Arguments)
    if err != nil {
        return h.errorResponse(req.ID, InternalError, "Tool execution failed", err)
    }
    
    // Return success response
    return h.successResponse(req.ID, result)
}

// Streaming response handler
func (h *ProtocolHandler) handleStreamingToolCall(ctx context.Context, execCtx *ExecutionContext, params ToolCallParams) ([]byte, error) {
    // Create streaming context
    streamCtx, cancel := context.WithCancel(ctx)
    defer cancel()
    
    stream := &StreamingResponse{
        ID:      execCtx.RequestID,
        Channel: make(chan StreamChunk, 100),
    }
    
    // Execute tool with streaming
    go func() {
        defer close(stream.Channel)
        
        handler := execCtx.Tool.StreamingHandler
        if handler == nil {
            // Fallback to regular handler
            result, err := execCtx.Tool.Handler(streamCtx, params.Arguments)
            stream.Channel <- StreamChunk{
                Type: "result",
                Data: result,
                Error: err,
            }
            return
        }
        
        // Execute streaming handler
        handler(streamCtx, params.Arguments, stream.Channel)
    }()
    
    // Return initial response indicating streaming
    return h.successResponse(execCtx.RequestID, map[string]interface{}{
        "type": "stream",
        "message": "Streaming response initiated",
    })
}
```

### Day 5: Transport Implementations

```go
// pkg/mcp/transport.go
package mcp

import (
    "bufio"
    "context"
    "fmt"
    "io"
    "net/http"
    "os"
)

// Transport interface for different MCP communication methods
type Transport interface {
    Start(ctx context.Context, handler MessageHandler) error
    Send(message []byte) error
    Close() error
}

// StdioTransport implements MCP over stdin/stdout
type StdioTransport struct {
    reader  *bufio.Reader
    writer  io.Writer
    handler MessageHandler
    done    chan struct{}
}

func NewStdioTransport() *StdioTransport {
    return &StdioTransport{
        reader: bufio.NewReader(os.Stdin),
        writer: os.Stdout,
        done:   make(chan struct{}),
    }
}

func (t *StdioTransport) Start(ctx context.Context, handler MessageHandler) error {
    t.handler = handler
    
    // Read loop
    go func() {
        defer close(t.done)
        
        for {
            select {
            case <-ctx.Done():
                return
            default:
                // Read message length header
                var length int32
                if err := binary.Read(t.reader, binary.LittleEndian, &length); err != nil {
                    if err != io.EOF {
                        handler.OnError(fmt.Errorf("read length: %w", err))
                    }
                    return
                }
                
                // Read message
                message := make([]byte, length)
                if _, err := io.ReadFull(t.reader, message); err != nil {
                    handler.OnError(fmt.Errorf("read message: %w", err))
                    return
                }
                
                // Handle message
                if err := handler.HandleMessage(ctx, message); err != nil {
                    handler.OnError(err)
                }
            }
        }
    }()
    
    return nil
}

func (t *StdioTransport) Send(message []byte) error {
    // Write length header
    length := int32(len(message))
    if err := binary.Write(t.writer, binary.LittleEndian, length); err != nil {
        return fmt.Errorf("write length: %w", err)
    }
    
    // Write message
    if _, err := t.writer.Write(message); err != nil {
        return fmt.Errorf("write message: %w", err)
    }
    
    return nil
}

// HTTPTransport implements MCP over HTTP
type HTTPTransport struct {
    server  *http.Server
    handler MessageHandler
}

func NewHTTPTransport(addr string) *HTTPTransport {
    return &HTTPTransport{
        server: &http.Server{
            Addr:         addr,
            ReadTimeout:  30 * time.Second,
            WriteTimeout: 30 * time.Second,
        },
    }
}

func (t *HTTPTransport) Start(ctx context.Context, handler MessageHandler) error {
    t.handler = handler
    
    mux := http.NewServeMux()
    mux.HandleFunc("/mcp", t.handleHTTP)
    mux.HandleFunc("/mcp/stream", t.handleSSE)
    
    t.server.Handler = mux
    
    go func() {
        <-ctx.Done()
        t.server.Shutdown(context.Background())
    }()
    
    return t.server.ListenAndServe()
}

func (t *HTTPTransport) handleHTTP(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }
    
    // Read body
    body, err := io.ReadAll(r.Body)
    if err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    
    // Handle message
    response, err := t.handler.HandleMessage(r.Context(), body)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    // Send response
    w.Header().Set("Content-Type", "application/json")
    w.Write(response)
}

// SSE Transport for streaming
type SSETransport struct {
    *HTTPTransport
    connections sync.Map
}

func (t *SSETransport) handleSSE(w http.ResponseWriter, r *http.Request) {
    // Set SSE headers
    w.Header().Set("Content-Type", "text/event-stream")
    w.Header().Set("Cache-Control", "no-cache")
    w.Header().Set("Connection", "keep-alive")
    
    flusher, ok := w.(http.Flusher)
    if !ok {
        http.Error(w, "Streaming not supported", http.StatusInternalServerError)
        return
    }
    
    // Create connection
    conn := &SSEConnection{
        ID:       generateConnID(),
        Writer:   w,
        Flusher:  flusher,
        Messages: make(chan SSEMessage, 100),
        Done:     make(chan struct{}),
    }
    
    // Register connection
    t.connections.Store(conn.ID, conn)
    defer t.connections.Delete(conn.ID)
    
    // Send initial connection event
    t.sendSSE(conn, SSEMessage{
        Event: "connected",
        Data:  map[string]string{"connection_id": conn.ID},
    })
    
    // Message loop
    for {
        select {
        case msg := <-conn.Messages:
            if err := t.sendSSE(conn, msg); err != nil {
                return
            }
        case <-r.Context().Done():
            return
        case <-conn.Done:
            return
        }
    }
}

func (t *SSETransport) sendSSE(conn *SSEConnection, msg SSEMessage) error {
    data, err := json.Marshal(msg.Data)
    if err != nil {
        return err
    }
    
    fmt.Fprintf(conn.Writer, "event: %s\n", msg.Event)
    fmt.Fprintf(conn.Writer, "data: %s\n\n", data)
    conn.Flusher.Flush()
    
    return nil
}
```

## Week 2: REST API & CLI Implementation

### Day 6-7: REST API with OpenAPI

```go
// pkg/api/rest/server.go
package rest

import (
    "context"
    "net/http"
    
    "github.com/gin-gonic/gin"
    "github.com/swaggo/files"
    "github.com/swaggo/gin-swagger"
)

// @title UDS REST API
// @version 1.0
// @description Universal Data Synthesizer REST API
// @host localhost:8080
// @BasePath /api/v1

type Server struct {
    discovery discovery.DiscoveryEngine
    patterns  patterns.PatternEngine
    query     query.QueryGenerator
    dashboard dashboard.DashboardBuilder
    
    router    *gin.Engine
    auth      *AuthMiddleware
    limiter   *RateLimiter
    metrics   *Metrics
}

func (s *Server) Setup() {
    s.router = gin.New()
    
    // Middleware
    s.router.Use(gin.Recovery())
    s.router.Use(s.metrics.Middleware())
    s.router.Use(s.auth.Middleware())
    s.router.Use(s.limiter.Middleware())
    
    // API routes
    v1 := s.router.Group("/api/v1")
    {
        // Discovery endpoints
        discovery := v1.Group("/discovery")
        {
            discovery.GET("/schemas", s.listSchemas)
            discovery.GET("/schemas/:name", s.getSchema)
            discovery.POST("/schemas/:name/profile", s.profileSchema)
            discovery.POST("/relationships", s.findRelationships)
        }
        
        // Analysis endpoints
        analysis := v1.Group("/analysis")
        {
            analysis.POST("/patterns", s.detectPatterns)
            analysis.POST("/quality", s.assessQuality)
            analysis.GET("/insights/:id", s.getInsights)
        }
        
        // Query endpoints
        query := v1.Group("/query")
        {
            query.POST("/generate", s.generateQuery)
            query.POST("/optimize", s.optimizeQuery)
            query.POST("/execute", s.executeQuery)
        }
        
        // Dashboard endpoints
        dashboard := v1.Group("/dashboard")
        {
            dashboard.POST("/create", s.createDashboard)
            dashboard.GET("/jobs/:id", s.getJobStatus)
            dashboard.GET("/jobs/:id/events", s.streamJobEvents)
        }
    }
    
    // Swagger documentation
    s.router.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))
    
    // Health check
    s.router.GET("/health", s.healthCheck)
}

// ListSchemas godoc
// @Summary List discovered schemas
// @Description Get a list of all discovered schemas with optional filtering
// @Tags discovery
// @Accept json
// @Produce json
// @Param filter query string false "Filter schemas by name pattern"
// @Param include_quality query bool false "Include quality metrics"
// @Success 200 {object} ListSchemasResponse
// @Failure 500 {object} ErrorResponse
// @Router /discovery/schemas [get]
func (s *Server) listSchemas(c *gin.Context) {
    ctx := c.Request.Context()
    
    // Parse query parameters
    filter := c.Query("filter")
    includeQuality := c.Query("include_quality") == "true"
    
    // Call discovery engine
    schemas, err := s.discovery.DiscoverSchemas(ctx, discovery.DiscoveryFilter{
        NamePattern: filter,
    })
    
    if err != nil {
        c.JSON(http.StatusInternalServerError, ErrorResponse{
            Error: err.Error(),
            Code:  "DISCOVERY_ERROR",
        })
        return
    }
    
    // Build response
    response := ListSchemasResponse{
        Schemas: make([]SchemaDTO, len(schemas)),
    }
    
    for i, schema := range schemas {
        dto := SchemaDTO{
            Name:           schema.Name,
            AttributeCount: len(schema.Attributes),
            SampleCount:    schema.SampleCount,
            LastAnalyzed:   schema.LastAnalyzedAt,
        }
        
        if includeQuality {
            dto.Quality = &QualityDTO{
                Score:  schema.Quality.OverallScore,
                Issues: len(schema.Quality.Issues),
            }
        }
        
        response.Schemas[i] = dto
    }
    
    c.JSON(http.StatusOK, response)
}

// CreateDashboard godoc
// @Summary Create a new dashboard
// @Description Generate a complete dashboard from a natural language goal
// @Tags dashboard
// @Accept json
// @Produce json
// @Param request body CreateDashboardRequest true "Dashboard creation request"
// @Success 202 {object} JobResponse "Job started successfully"
// @Failure 400 {object} ErrorResponse "Invalid request"
// @Failure 500 {object} ErrorResponse "Server error"
// @Router /dashboard/create [post]
func (s *Server) createDashboard(c *gin.Context) {
    var req CreateDashboardRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, ErrorResponse{
            Error: err.Error(),
            Code:  "INVALID_REQUEST",
        })
        return
    }
    
    // Validate request
    if err := req.Validate(); err != nil {
        c.JSON(http.StatusBadRequest, ErrorResponse{
            Error: err.Error(),
            Code:  "VALIDATION_ERROR",
        })
        return
    }
    
    // Start async job
    job := &DashboardJob{
        ID:        generateJobID(),
        Goal:      req.Goal,
        Style:     req.Style,
        Status:    JobStatusPending,
        CreatedAt: time.Now(),
    }
    
    // Save job
    if err := s.jobStore.Create(job); err != nil {
        c.JSON(http.StatusInternalServerError, ErrorResponse{
            Error: "Failed to create job",
            Code:  "JOB_CREATE_ERROR",
        })
        return
    }
    
    // Start processing
    go s.processDashboardJob(job)
    
    // Return job info
    c.JSON(http.StatusAccepted, JobResponse{
        JobID:     job.ID,
        Status:    job.Status,
        StatusURL: fmt.Sprintf("/api/v1/dashboard/jobs/%s", job.ID),
        EventsURL: fmt.Sprintf("/api/v1/dashboard/jobs/%s/events", job.ID),
    })
}

// SSE endpoint for job progress
func (s *Server) streamJobEvents(c *gin.Context) {
    jobID := c.Param("id")
    
    // Verify job exists
    job, err := s.jobStore.Get(jobID)
    if err != nil {
        c.JSON(http.StatusNotFound, ErrorResponse{
            Error: "Job not found",
            Code:  "JOB_NOT_FOUND",
        })
        return
    }
    
    // Set SSE headers
    c.Writer.Header().Set("Content-Type", "text/event-stream")
    c.Writer.Header().Set("Cache-Control", "no-cache")
    c.Writer.Header().Set("Connection", "keep-alive")
    
    // Create event channel
    events := s.jobEvents.Subscribe(jobID)
    defer s.jobEvents.Unsubscribe(jobID, events)
    
    // Send initial status
    s.sendSSEEvent(c.Writer, Event{
        Type: "status",
        Data: map[string]interface{}{
            "status":   job.Status,
            "progress": job.Progress,
        },
    })
    
    // Stream events
    for {
        select {
        case event := <-events:
            if err := s.sendSSEEvent(c.Writer, event); err != nil {
                return
            }
        case <-c.Request.Context().Done():
            return
        }
    }
}
```

### Day 8-9: CLI Tool Implementation

```go
// pkg/cli/main.go
package main

import (
    "fmt"
    "os"
    
    "github.com/spf13/cobra"
    "github.com/spf13/viper"
)

var (
    cfgFile string
    client  *UDSClient
)

func main() {
    if err := rootCmd.Execute(); err != nil {
        fmt.Fprintln(os.Stderr, err)
        os.Exit(1)
    }
}

var rootCmd = &cobra.Command{
    Use:   "uds",
    Short: "Universal Data Synthesizer CLI",
    Long: `UDS CLI provides command-line access to all UDS capabilities including
schema discovery, pattern analysis, and dashboard generation.`,
    PersistentPreRun: func(cmd *cobra.Command, args []string) {
        initConfig()
        initClient()
    },
}

func init() {
    rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is $HOME/.uds.yaml)")
    rootCmd.PersistentFlags().String("server", "http://localhost:8080", "UDS server URL")
    rootCmd.PersistentFlags().String("output", "json", "Output format (json, yaml, table)")
    
    viper.BindPFlag("server", rootCmd.PersistentFlags().Lookup("server"))
    viper.BindPFlag("output", rootCmd.PersistentFlags().Lookup("output"))
    
    // Add subcommands
    rootCmd.AddCommand(discoveryCmd)
    rootCmd.AddCommand(analyzeCmd)
    rootCmd.AddCommand(queryCmd)
    rootCmd.AddCommand(dashboardCmd)
    rootCmd.AddCommand(interactiveCmd)
}

// Discovery commands
var discoveryCmd = &cobra.Command{
    Use:   "discover",
    Short: "Schema discovery operations",
}

var listSchemasCmd = &cobra.Command{
    Use:   "list",
    Short: "List all discovered schemas",
    RunE: func(cmd *cobra.Command, args []string) error {
        filter, _ := cmd.Flags().GetString("filter")
        includeQuality, _ := cmd.Flags().GetBool("quality")
        
        schemas, err := client.ListSchemas(ListSchemasOptions{
            Filter:         filter,
            IncludeQuality: includeQuality,
        })
        
        if err != nil {
            return fmt.Errorf("failed to list schemas: %w", err)
        }
        
        return outputResult(schemas)
    },
}

var profileSchemaCmd = &cobra.Command{
    Use:   "profile [schema]",
    Short: "Profile a specific schema",
    Args:  cobra.ExactArgs(1),
    RunE: func(cmd *cobra.Command, args []string) error {
        depth, _ := cmd.Flags().GetString("depth")
        attributes, _ := cmd.Flags().GetStringSlice("attributes")
        
        // Show progress spinner
        spinner := NewSpinner("Profiling schema...")
        spinner.Start()
        
        profile, err := client.ProfileSchema(args[0], ProfileOptions{
            Depth:      depth,
            Attributes: attributes,
        })
        
        spinner.Stop()
        
        if err != nil {
            return fmt.Errorf("failed to profile schema: %w", err)
        }
        
        return outputResult(profile)
    },
}

func init() {
    discoveryCmd.AddCommand(listSchemasCmd)
    discoveryCmd.AddCommand(profileSchemaCmd)
    discoveryCmd.AddCommand(findRelationshipsCmd)
    
    listSchemasCmd.Flags().StringP("filter", "f", "", "Filter schemas by pattern")
    listSchemasCmd.Flags().BoolP("quality", "q", false, "Include quality metrics")
    
    profileSchemaCmd.Flags().StringP("depth", "d", "full", "Profile depth (basic, standard, full)")
    profileSchemaCmd.Flags().StringSliceP("attributes", "a", []string{}, "Specific attributes to profile")
}

// Interactive mode
var interactiveCmd = &cobra.Command{
    Use:   "interactive",
    Short: "Start interactive UDS session",
    RunE: func(cmd *cobra.Command, args []string) error {
        return runInteractiveMode()
    },
}

func runInteractiveMode() error {
    fmt.Println("Welcome to UDS Interactive Mode")
    fmt.Println("Type 'help' for available commands or 'exit' to quit")
    fmt.Println()
    
    rl, err := readline.New("> ")
    if err != nil {
        return err
    }
    defer rl.Close()
    
    // Command completion
    rl.Config.AutoComplete = &UDSCompleter{
        client: client,
    }
    
    for {
        line, err := rl.Readline()
        if err != nil {
            break
        }
        
        if line == "exit" || line == "quit" {
            break
        }
        
        if err := processInteractiveCommand(line); err != nil {
            fmt.Printf("Error: %v\n", err)
        }
    }
    
    return nil
}

// Dashboard creation with progress streaming
var createDashboardCmd = &cobra.Command{
    Use:   "create [goal]",
    Short: "Create a dashboard from natural language goal",
    Args:  cobra.MinimumNArgs(1),
    RunE: func(cmd *cobra.Command, args []string) error {
        goal := strings.Join(args, " ")
        style, _ := cmd.Flags().GetString("style")
        follow, _ := cmd.Flags().GetBool("follow")
        
        // Start dashboard creation
        job, err := client.CreateDashboard(CreateDashboardRequest{
            Goal:  goal,
            Style: style,
        })
        
        if err != nil {
            return fmt.Errorf("failed to create dashboard: %w", err)
        }
        
        fmt.Printf("Dashboard job started: %s\n", job.ID)
        
        if !follow {
            fmt.Printf("Check status with: uds dashboard status %s\n", job.ID)
            return nil
        }
        
        // Stream progress
        fmt.Println("Following progress...")
        return streamJobProgress(job.ID)
    },
}

func streamJobProgress(jobID string) error {
    events, err := client.StreamJobEvents(jobID)
    if err != nil {
        return err
    }
    
    progressBar := NewProgressBar(100)
    
    for event := range events {
        switch event.Type {
        case "progress":
            progress := event.Data["progress"].(float64)
            message := event.Data["message"].(string)
            progressBar.Update(int(progress), message)
            
        case "phase_complete":
            phase := event.Data["phase"].(string)
            fmt.Printf("✓ Completed: %s\n", phase)
            
        case "insight":
            insight := event.Data["insight"].(string)
            fmt.Printf("💡 Insight: %s\n", insight)
            
        case "complete":
            progressBar.Finish()
            result := event.Data["result"].(map[string]interface{})
            fmt.Printf("\n✅ Dashboard created successfully!\n")
            fmt.Printf("URL: %s\n", result["url"])
            return nil
            
        case "error":
            progressBar.Finish()
            return fmt.Errorf("job failed: %s", event.Data["error"])
        }
    }
    
    return nil
}
```

### Day 10: Client Libraries

```go
// pkg/client/client.go
package client

import (
    "bytes"
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "time"
)

// UDSClient provides programmatic access to UDS
type UDSClient struct {
    baseURL    string
    httpClient *http.Client
    apiKey     string
    
    // Service clients
    Discovery  *DiscoveryClient
    Analysis   *AnalysisClient
    Query      *QueryClient
    Dashboard  *DashboardClient
}

func NewClient(config ClientConfig) *UDSClient {
    httpClient := &http.Client{
        Timeout: config.Timeout,
    }
    
    if config.Transport != nil {
        httpClient.Transport = config.Transport
    }
    
    client := &UDSClient{
        baseURL:    config.BaseURL,
        httpClient: httpClient,
        apiKey:     config.APIKey,
    }
    
    // Initialize service clients
    client.Discovery = &DiscoveryClient{client: client}
    client.Analysis = &AnalysisClient{client: client}
    client.Query = &QueryClient{client: client}
    client.Dashboard = &DashboardClient{client: client}
    
    return client
}

// Generic request method
func (c *UDSClient) request(ctx context.Context, method, path string, body interface{}) (*http.Response, error) {
    url := c.baseURL + path
    
    var bodyReader io.Reader
    if body != nil {
        data, err := json.Marshal(body)
        if err != nil {
            return nil, fmt.Errorf("marshal body: %w", err)
        }
        bodyReader = bytes.NewReader(data)
    }
    
    req, err := http.NewRequestWithContext(ctx, method, url, bodyReader)
    if err != nil {
        return nil, fmt.Errorf("create request: %w", err)
    }
    
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("Accept", "application/json")
    
    if c.apiKey != "" {
        req.Header.Set("Authorization", "Bearer "+c.apiKey)
    }
    
    resp, err := c.httpClient.Do(req)
    if err != nil {
        return nil, fmt.Errorf("execute request: %w", err)
    }
    
    if resp.StatusCode >= 400 {
        defer resp.Body.Close()
        var errResp ErrorResponse
        if err := json.NewDecoder(resp.Body).Decode(&errResp); err != nil {
            return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, resp.Status)
        }
        return nil, &APIError{
            StatusCode: resp.StatusCode,
            Code:       errResp.Code,
            Message:    errResp.Error,
        }
    }
    
    return resp, nil
}

// Discovery client
type DiscoveryClient struct {
    client *UDSClient
}

func (d *DiscoveryClient) ListSchemas(ctx context.Context, opts ListSchemasOptions) (*ListSchemasResponse, error) {
    path := "/api/v1/discovery/schemas"
    if opts.Filter != "" {
        path += "?filter=" + url.QueryEscape(opts.Filter)
    }
    
    resp, err := d.client.request(ctx, "GET", path, nil)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    var result ListSchemasResponse
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, fmt.Errorf("decode response: %w", err)
    }
    
    return &result, nil
}

// TypeScript client
const typescriptClient = `
// client/typescript/src/index.ts
export class UDSClient {
    private baseURL: string;
    private apiKey?: string;
    
    constructor(config: ClientConfig) {
        this.baseURL = config.baseURL;
        this.apiKey = config.apiKey;
    }
    
    // Schema discovery
    async listSchemas(options?: ListSchemasOptions): Promise<Schema[]> {
        const params = new URLSearchParams();
        if (options?.filter) params.append('filter', options.filter);
        if (options?.includeQuality) params.append('include_quality', 'true');
        
        const response = await this.request('/api/v1/discovery/schemas?' + params);
        return response.schemas;
    }
    
    // Dashboard creation with progress streaming
    async createDashboard(goal: string, options?: CreateDashboardOptions): Promise<DashboardJob> {
        const job = await this.request('/api/v1/dashboard/create', {
            method: 'POST',
            body: JSON.stringify({ goal, ...options })
        });
        
        // Return job with streaming capability
        return {
            ...job,
            streamProgress: () => this.streamJobProgress(job.jobId)
        };
    }
    
    private async streamJobProgress(jobId: string): AsyncIterableIterator<JobEvent> {
        const eventsUrl = '${this.baseURL}/api/v1/dashboard/jobs/${jobId}/events';
        const eventSource = new EventSource(eventsUrl);
        
        const events = new EventChannel<JobEvent>();
        
        eventSource.onmessage = (e) => {
            const event = JSON.parse(e.data) as JobEvent;
            events.push(event);
            
            if (event.type === 'complete' || event.type === 'error') {
                eventSource.close();
                events.close();
            }
        };
        
        eventSource.onerror = (e) => {
            eventSource.close();
            events.error(new Error('Stream error'));
        };
        
        return events;
    }
}
`
```

## Week 3: SSE Streaming & Integration

### Day 11-12: Advanced SSE Implementation

```go
// pkg/streaming/sse_manager.go
package streaming

import (
    "context"
    "encoding/json"
    "fmt"
    "sync"
    "time"
)

// SSEManager handles all SSE connections and event distribution
type SSEManager struct {
    connections sync.Map // jobID -> []*Connection
    events      chan Event
    metrics     *Metrics
}

type Event struct {
    JobID     string
    Type      EventType
    Data      interface{}
    Timestamp time.Time
}

type Connection struct {
    ID       string
    JobID    string
    Writer   http.ResponseWriter
    Flusher  http.Flusher
    Events   chan Event
    Done     chan struct{}
    Created  time.Time
}

func (m *SSEManager) HandleConnection(w http.ResponseWriter, r *http.Request, jobID string) {
    // Check if SSE is supported
    flusher, ok := w.(http.Flusher)
    if !ok {
        http.Error(w, "Streaming not supported", http.StatusInternalServerError)
        return
    }
    
    // Set headers
    w.Header().Set("Content-Type", "text/event-stream")
    w.Header().Set("Cache-Control", "no-cache")
    w.Header().Set("Connection", "keep-alive")
    w.Header().Set("X-Accel-Buffering", "no") // Disable Nginx buffering
    
    // Create connection
    conn := &Connection{
        ID:      generateConnID(),
        JobID:   jobID,
        Writer:  w,
        Flusher: flusher,
        Events:  make(chan Event, 100),
        Done:    make(chan struct{}),
        Created: time.Now(),
    }
    
    // Register connection
    m.addConnection(jobID, conn)
    defer m.removeConnection(jobID, conn)
    
    // Send initial connection event
    m.sendEvent(conn, Event{
        Type: EventTypeConnected,
        Data: map[string]string{
            "connectionId": conn.ID,
            "jobId":        jobID,
        },
    })
    
    // Heartbeat ticker
    heartbeat := time.NewTicker(30 * time.Second)
    defer heartbeat.Stop()
    
    // Event loop
    for {
        select {
        case event := <-conn.Events:
            if err := m.sendEvent(conn, event); err != nil {
                m.metrics.IncrementConnectionError()
                return
            }
            
        case <-heartbeat.C:
            if err := m.sendHeartbeat(conn); err != nil {
                return
            }
            
        case <-r.Context().Done():
            m.sendEvent(conn, Event{
                Type: EventTypeDisconnected,
                Data: map[string]string{"reason": "client_disconnect"},
            })
            return
            
        case <-conn.Done:
            return
        }
    }
}

func (m *SSEManager) sendEvent(conn *Connection, event Event) error {
    data, err := json.Marshal(event.Data)
    if err != nil {
        return fmt.Errorf("marshal event: %w", err)
    }
    
    // Format SSE message
    _, err = fmt.Fprintf(conn.Writer, "id: %d\n", time.Now().UnixNano())
    if err != nil {
        return err
    }
    
    _, err = fmt.Fprintf(conn.Writer, "event: %s\n", event.Type)
    if err != nil {
        return err
    }
    
    _, err = fmt.Fprintf(conn.Writer, "data: %s\n\n", data)
    if err != nil {
        return err
    }
    
    conn.Flusher.Flush()
    
    m.metrics.IncrementEventsSent(string(event.Type))
    return nil
}

// Broadcast event to all connections for a job
func (m *SSEManager) BroadcastJobEvent(jobID string, eventType EventType, data interface{}) {
    event := Event{
        JobID:     jobID,
        Type:      eventType,
        Data:      data,
        Timestamp: time.Now(),
    }
    
    // Get all connections for this job
    if conns, ok := m.connections.Load(jobID); ok {
        connections := conns.([]*Connection)
        
        for _, conn := range connections {
            select {
            case conn.Events <- event:
                // Sent successfully
            default:
                // Connection is slow, skip this event
                m.metrics.IncrementDroppedEvents()
            }
        }
    }
}

// Progress tracking for long-running operations
type ProgressTracker struct {
    manager    *SSEManager
    jobID      string
    totalSteps int
    current    int
    mu         sync.Mutex
}

func (t *ProgressTracker) Update(step int, message string) {
    t.mu.Lock()
    t.current = step
    progress := float64(step) / float64(t.totalSteps) * 100
    t.mu.Unlock()
    
    t.manager.BroadcastJobEvent(t.jobID, EventTypeProgress, map[string]interface{}{
        "step":     step,
        "total":    t.totalSteps,
        "progress": progress,
        "message":  message,
    })
}

func (t *ProgressTracker) CompletePhase(phase string, results interface{}) {
    t.manager.BroadcastJobEvent(t.jobID, EventTypePhaseComplete, map[string]interface{}{
        "phase":   phase,
        "results": results,
    })
}

func (t *ProgressTracker) AddInsight(insight Insight) {
    t.manager.BroadcastJobEvent(t.jobID, EventTypeInsight, map[string]interface{}{
        "type":        insight.Type,
        "title":       insight.Title,
        "description": insight.Description,
        "confidence":  insight.Confidence,
    })
}
```

### Day 13-14: Authentication & Rate Limiting

```go
// pkg/api/middleware/auth.go
package middleware

import (
    "context"
    "fmt"
    "strings"
    "time"
    
    "github.com/golang-jwt/jwt/v4"
    "github.com/gin-gonic/gin"
)

type AuthMiddleware struct {
    jwtSecret   []byte
    apiKeyStore APIKeyStore
    userStore   UserStore
}

type Claims struct {
    UserID   string   `json:"user_id"`
    TenantID string   `json:"tenant_id"`
    Scopes   []string `json:"scopes"`
    jwt.RegisteredClaims
}

func (a *AuthMiddleware) Middleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        // Check for API key first
        if apiKey := c.GetHeader("X-API-Key"); apiKey != "" {
            if err := a.validateAPIKey(c, apiKey); err != nil {
                c.JSON(401, gin.H{"error": "Invalid API key"})
                c.Abort()
                return
            }
            c.Next()
            return
        }
        
        // Check for JWT token
        authHeader := c.GetHeader("Authorization")
        if authHeader == "" {
            c.JSON(401, gin.H{"error": "No authorization provided"})
            c.Abort()
            return
        }
        
        // Extract token
        parts := strings.Split(authHeader, " ")
        if len(parts) != 2 || parts[0] != "Bearer" {
            c.JSON(401, gin.H{"error": "Invalid authorization header"})
            c.Abort()
            return
        }
        
        // Validate JWT
        claims, err := a.validateJWT(parts[1])
        if err != nil {
            c.JSON(401, gin.H{"error": "Invalid token"})
            c.Abort()
            return
        }
        
        // Set user context
        c.Set("user_id", claims.UserID)
        c.Set("tenant_id", claims.TenantID)
        c.Set("scopes", claims.Scopes)
        
        c.Next()
    }
}

func (a *AuthMiddleware) validateJWT(tokenString string) (*Claims, error) {
    token, err := jwt.ParseWithClaims(tokenString, &Claims{}, func(token *jwt.Token) (interface{}, error) {
        if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
            return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
        }
        return a.jwtSecret, nil
    })
    
    if err != nil {
        return nil, err
    }
    
    if claims, ok := token.Claims.(*Claims); ok && token.Valid {
        return claims, nil
    }
    
    return nil, fmt.Errorf("invalid token")
}

// Rate limiting middleware
type RateLimiter struct {
    store       RateLimitStore
    defaultRate int
    burst       int
}

func (r *RateLimiter) Middleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        // Get identifier (user ID or IP)
        identifier := r.getIdentifier(c)
        
        // Get rate limit for this identifier
        limit := r.getLimit(c, identifier)
        
        // Check rate limit
        allowed, remaining, resetAt := r.store.Allow(identifier, limit)
        
        // Set headers
        c.Header("X-RateLimit-Limit", fmt.Sprintf("%d", limit.Requests))
        c.Header("X-RateLimit-Remaining", fmt.Sprintf("%d", remaining))
        c.Header("X-RateLimit-Reset", fmt.Sprintf("%d", resetAt.Unix()))
        
        if !allowed {
            c.JSON(429, gin.H{
                "error": "Rate limit exceeded",
                "retry_after": resetAt.Unix(),
            })
            c.Abort()
            return
        }
        
        c.Next()
    }
}

func (r *RateLimiter) getIdentifier(c *gin.Context) string {
    // Prefer user ID if authenticated
    if userID, exists := c.Get("user_id"); exists {
        return fmt.Sprintf("user:%s", userID)
    }
    
    // Fall back to IP
    return fmt.Sprintf("ip:%s", c.ClientIP())
}

// Multi-tenant data isolation
type TenantMiddleware struct {
    tenantStore TenantStore
}

func (t *TenantMiddleware) Middleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        tenantID, exists := c.Get("tenant_id")
        if !exists {
            c.JSON(400, gin.H{"error": "No tenant context"})
            c.Abort()
            return
        }
        
        // Verify tenant is active
        tenant, err := t.tenantStore.Get(tenantID.(string))
        if err != nil || !tenant.Active {
            c.JSON(403, gin.H{"error": "Invalid tenant"})
            c.Abort()
            return
        }
        
        // Set tenant context for data isolation
        ctx := context.WithValue(c.Request.Context(), "tenant", tenant)
        c.Request = c.Request.WithContext(ctx)
        
        c.Next()
    }
}
```

### Day 15: Testing & Documentation

```go
// pkg/interface/integration_test.go
package interface

import (
    "bytes"
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "testing"
    "time"
    
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/suite"
)

type InterfaceTestSuite struct {
    suite.Suite
    mcpServer  *MCP.Server
    restServer *rest.Server
    client     *client.UDSClient
}

func (s *InterfaceTestSuite) SetupSuite() {
    // Create mock services
    discovery := discovery.NewMockEngine()
    patterns := patterns.NewMockEngine()
    
    // Setup MCP server
    s.mcpServer = mcp.NewServer(mcp.ServerConfig{
        TransportType: mcp.TransportHTTP,
    })
    s.mcpServer.SetDiscovery(discovery)
    s.mcpServer.SetPatterns(patterns)
    
    // Setup REST server
    s.restServer = rest.NewServer()
    s.restServer.SetDiscovery(discovery)
    s.restServer.SetPatterns(patterns)
    
    // Create test client
    s.client = client.NewClient(client.ClientConfig{
        BaseURL: "http://localhost:8080",
    })
}

func (s *InterfaceTestSuite) TestMCPToolCall() {
    // Test discover schemas tool
    request := mcp.Request{
        Jsonrpc: "2.0",
        Method:  "tools/call",
        Params: json.RawMessage(`{
            "name": "discovery.list_schemas",
            "arguments": {
                "filter": "Transaction"
            }
        }`),
        ID: 1,
    }
    
    response := s.callMCP(request)
    
    assert.Equal(s.T(), "2.0", response.Jsonrpc)
    assert.Nil(s.T(), response.Error)
    assert.NotNil(s.T(), response.Result)
    
    // Verify result structure
    result := response.Result.(map[string]interface{})
    schemas := result["schemas"].([]interface{})
    assert.Greater(s.T(), len(schemas), 0)
}

func (s *InterfaceTestSuite) TestRESTAPIFlow() {
    // Test complete dashboard creation flow
    
    // 1. List schemas
    schemas, err := s.client.Discovery.ListSchemas(context.Background(), client.ListSchemasOptions{})
    assert.NoError(s.T(), err)
    assert.Greater(s.T(), len(schemas.Schemas), 0)
    
    // 2. Profile a schema
    profile, err := s.client.Discovery.ProfileSchema(context.Background(), "Transaction", client.ProfileOptions{
        Depth: "full",
    })
    assert.NoError(s.T(), err)
    assert.NotNil(s.T(), profile)
    
    // 3. Create dashboard
    job, err := s.client.Dashboard.Create(context.Background(), client.CreateDashboardRequest{
        Goal: "Analyze transaction performance",
    })
    assert.NoError(s.T(), err)
    assert.NotEmpty(s.T(), job.JobID)
    
    // 4. Stream progress
    events := make([]client.JobEvent, 0)
    eventChan, err := s.client.Dashboard.StreamProgress(context.Background(), job.JobID)
    assert.NoError(s.T(), err)
    
    timeout := time.After(10 * time.Second)
    for {
        select {
        case event := <-eventChan:
            events = append(events, event)
            if event.Type == "complete" || event.Type == "error" {
                goto done
            }
        case <-timeout:
            s.T().Fatal("Timeout waiting for job completion")
        }
    }
    
done:
    // Verify we got expected events
    assert.Greater(s.T(), len(events), 0)
    
    // Find completion event
    var completionEvent *client.JobEvent
    for _, e := range events {
        if e.Type == "complete" {
            completionEvent = &e
            break
        }
    }
    
    assert.NotNil(s.T(), completionEvent)
}

func (s *InterfaceTestSuite) TestSSEStreaming() {
    // Create test server
    server := httptest.NewServer(s.restServer.Router())
    defer server.Close()
    
    // Start a job
    resp, err := http.Post(
        server.URL+"/api/v1/dashboard/create",
        "application/json",
        bytes.NewReader([]byte(`{"goal":"test dashboard"}`)),
    )
    assert.NoError(s.T(), err)
    
    var job JobResponse
    json.NewDecoder(resp.Body).Decode(&job)
    
    // Connect to SSE stream
    sseResp, err := http.Get(server.URL + "/api/v1/dashboard/jobs/" + job.JobID + "/events")
    assert.NoError(s.T(), err)
    defer sseResp.Body.Close()
    
    assert.Equal(s.T(), "text/event-stream", sseResp.Header.Get("Content-Type"))
    
    // Read events
    scanner := bufio.NewScanner(sseResp.Body)
    eventCount := 0
    
    for scanner.Scan() {
        line := scanner.Text()
        if strings.HasPrefix(line, "event:") {
            eventCount++
        }
    }
    
    assert.Greater(s.T(), eventCount, 0)
}

// Benchmark tests
func BenchmarkMCPToolCall(b *testing.B) {
    server := setupBenchmarkServer()
    
    request := mcp.Request{
        Jsonrpc: "2.0",
        Method:  "tools/call",
        Params: json.RawMessage(`{
            "name": "discovery.list_schemas",
            "arguments": {}
        }`),
        ID: 1,
    }
    
    b.ResetTimer()
    
    for i := 0; i < b.N; i++ {
        server.HandleRequest(context.Background(), request)
    }
}

func BenchmarkRESTEndpoint(b *testing.B) {
    server := setupBenchmarkServer()
    
    b.RunParallel(func(pb *testing.PB) {
        for pb.Next() {
            resp, _ := http.Get("http://localhost:8080/api/v1/discovery/schemas")
            resp.Body.Close()
        }
    })
}
```

## Week 4: Production Polish

### Day 16-17: Error Handling & Resilience

```go
// pkg/interface/errors.go
package interface

import (
    "fmt"
    "net/http"
)

// Structured error types
type ErrorCode string

const (
    ErrorCodeInvalidRequest   ErrorCode = "INVALID_REQUEST"
    ErrorCodeNotFound        ErrorCode = "NOT_FOUND"
    ErrorCodeUnauthorized    ErrorCode = "UNAUTHORIZED"
    ErrorCodeRateLimited     ErrorCode = "RATE_LIMITED"
    ErrorCodeInternal        ErrorCode = "INTERNAL_ERROR"
    ErrorCodeServiceUnavailable ErrorCode = "SERVICE_UNAVAILABLE"
)

type APIError struct {
    Code       ErrorCode              `json:"code"`
    Message    string                 `json:"message"`
    Details    map[string]interface{} `json:"details,omitempty"`
    TraceID    string                 `json:"trace_id,omitempty"`
    StatusCode int                    `json:"-"`
}

func (e *APIError) Error() string {
    return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

// Error handler middleware
func ErrorHandler() gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Next()
        
        // Handle any errors that occurred
        if len(c.Errors) > 0 {
            err := c.Errors.Last()
            
            // Convert to API error
            apiErr := toAPIError(err.Err)
            
            // Add trace ID
            if traceID, exists := c.Get("trace_id"); exists {
                apiErr.TraceID = traceID.(string)
            }
            
            // Log error
            logError(c, apiErr)
            
            // Send response
            c.JSON(apiErr.StatusCode, apiErr)
        }
    }
}

// Circuit breaker for external services
type CircuitBreaker struct {
    name           string
    maxFailures    int
    resetTimeout   time.Duration
    
    mu             sync.Mutex
    failures       int
    lastFailure    time.Time
    state          CircuitState
}

func (cb *CircuitBreaker) Call(fn func() error) error {
    cb.mu.Lock()
    
    // Check if circuit should be reset
    if cb.state == StateOpen && time.Since(cb.lastFailure) > cb.resetTimeout {
        cb.state = StateHalfOpen
        cb.failures = 0
    }
    
    if cb.state == StateOpen {
        cb.mu.Unlock()
        return fmt.Errorf("circuit breaker is open")
    }
    
    cb.mu.Unlock()
    
    // Execute function
    err := fn()
    
    cb.mu.Lock()
    defer cb.mu.Unlock()
    
    if err != nil {
        cb.failures++
        cb.lastFailure = time.Now()
        
        if cb.failures >= cb.maxFailures {
            cb.state = StateOpen
        }
        
        return err
    }
    
    // Success - reset failures
    cb.failures = 0
    cb.state = StateClosed
    
    return nil
}

// Graceful shutdown
type GracefulShutdown struct {
    servers   []Server
    timeout   time.Duration
    onShutdown []func()
}

func (g *GracefulShutdown) Shutdown(ctx context.Context) error {
    // Create shutdown context with timeout
    shutdownCtx, cancel := context.WithTimeout(ctx, g.timeout)
    defer cancel()
    
    // Run pre-shutdown hooks
    for _, hook := range g.onShutdown {
        hook()
    }
    
    // Shutdown all servers
    var wg sync.WaitGroup
    errors := make(chan error, len(g.servers))
    
    for _, server := range g.servers {
        wg.Add(1)
        go func(s Server) {
            defer wg.Done()
            if err := s.Shutdown(shutdownCtx); err != nil {
                errors <- err
            }
        }(server)
    }
    
    wg.Wait()
    close(errors)
    
    // Collect errors
    var shutdownErrors []error
    for err := range errors {
        shutdownErrors = append(shutdownErrors, err)
    }
    
    if len(shutdownErrors) > 0 {
        return fmt.Errorf("shutdown errors: %v", shutdownErrors)
    }
    
    return nil
}
```

### Day 18-19: Performance Optimization

```go
// pkg/interface/performance.go
package interface

import (
    "sync"
    "time"
)

// Connection pooling for MCP
type ConnectionPool struct {
    factory    ConnectionFactory
    pool       chan Connection
    maxSize    int
    maxIdleTime time.Duration
}

func NewConnectionPool(factory ConnectionFactory, size int) *ConnectionPool {
    return &ConnectionPool{
        factory:     factory,
        pool:        make(chan Connection, size),
        maxSize:     size,
        maxIdleTime: 5 * time.Minute,
    }
}

func (p *ConnectionPool) Get() (Connection, error) {
    select {
    case conn := <-p.pool:
        // Check if connection is still valid
        if time.Since(conn.LastUsed()) < p.maxIdleTime && conn.IsAlive() {
            return conn, nil
        }
        // Connection expired, close it
        conn.Close()
        
    default:
        // Pool empty, create new connection
    }
    
    return p.factory.Create()
}

func (p *ConnectionPool) Put(conn Connection) {
    select {
    case p.pool <- conn:
        // Connection returned to pool
    default:
        // Pool full, close connection
        conn.Close()
    }
}

// Response caching
type ResponseCache struct {
    cache    *lru.Cache
    ttl      time.Duration
    mu       sync.RWMutex
}

func (c *ResponseCache) Middleware() gin.HandlerFunc {
    return func(ctx *gin.Context) {
        // Only cache GET requests
        if ctx.Request.Method != http.MethodGet {
            ctx.Next()
            return
        }
        
        // Generate cache key
        key := c.generateKey(ctx.Request)
        
        // Check cache
        c.mu.RLock()
        if cached, found := c.cache.Get(key); found {
            c.mu.RUnlock()
            
            entry := cached.(*CacheEntry)
            if time.Since(entry.Timestamp) < c.ttl {
                // Serve from cache
                ctx.Data(entry.StatusCode, entry.ContentType, entry.Data)
                ctx.Abort()
                return
            }
        }
        c.mu.RUnlock()
        
        // Capture response
        writer := &responseWriter{ResponseWriter: ctx.Writer}
        ctx.Writer = writer
        
        ctx.Next()
        
        // Cache successful responses
        if writer.statusCode >= 200 && writer.statusCode < 300 {
            c.mu.Lock()
            c.cache.Add(key, &CacheEntry{
                StatusCode:  writer.statusCode,
                ContentType: writer.Header().Get("Content-Type"),
                Data:        writer.body.Bytes(),
                Timestamp:   time.Now(),
            })
            c.mu.Unlock()
        }
    }
}

// Request batching for efficiency
type RequestBatcher struct {
    batchSize    int
    batchTimeout time.Duration
    processor    BatchProcessor
    
    mu           sync.Mutex
    batch        []Request
    timer        *time.Timer
}

func (b *RequestBatcher) Add(req Request) {
    b.mu.Lock()
    defer b.mu.Unlock()
    
    b.batch = append(b.batch, req)
    
    if len(b.batch) >= b.batchSize {
        b.processBatch()
    } else if b.timer == nil {
        b.timer = time.AfterFunc(b.batchTimeout, func() {
            b.mu.Lock()
            defer b.mu.Unlock()
            b.processBatch()
        })
    }
}

func (b *RequestBatcher) processBatch() {
    if len(b.batch) == 0 {
        return
    }
    
    batch := b.batch
    b.batch = nil
    
    if b.timer != nil {
        b.timer.Stop()
        b.timer = nil
    }
    
    go b.processor.ProcessBatch(batch)
}
```

### Day 20: Deployment & Documentation

```yaml
# deployments/interface/docker-compose.yml
version: '3.8'

services:
  # MCP Server
  mcp-server:
    build:
      context: .
      dockerfile: Dockerfile.mcp
    ports:
      - "9090:9090"  # HTTP/SSE transport
    environment:
      - MCP_TRANSPORT=http
      - MCP_AUTH_ENABLED=true
      - DISCOVERY_URL=http://discovery:8080
      - PATTERNS_URL=http://patterns:8081
    depends_on:
      - discovery
      - patterns
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      
  # REST API Server
  rest-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8080:8080"
    environment:
      - GIN_MODE=release
      - API_AUTH_ENABLED=true
      - JWT_SECRET=${JWT_SECRET}
      - RATE_LIMIT_ENABLED=true
      - CACHE_ENABLED=true
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
    depends_on:
      - redis
      - postgres
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      
  # Nginx for load balancing and SSL
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - mcp-server
      - rest-api
      
  # Redis for caching and rate limiting
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
      
  # OpenTelemetry Collector
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"  # OTLP gRPC receiver
      
volumes:
  redis_data:
```

```go
// Final documentation
/*
Package interface provides multiple ways to interact with the UDS system:

1. MCP Server - For AI agents (Copilot, Claude)
   - JSON-RPC 2.0 protocol
   - Supports stdio, HTTP, and SSE transports
   - Tool-based interface with streaming support

2. REST API - For applications
   - OpenAPI 3.0 documented
   - Full CRUD operations
   - SSE endpoints for real-time updates

3. CLI Tool - For developers
   - Interactive and batch modes
   - Progress visualization
   - Shell completion

4. Client Libraries - For programmatic access
   - Go, TypeScript, Python
   - Automatic retries and error handling
   - Streaming support

Architecture:
- Transport agnostic design
- Pluggable authentication (JWT, API keys)
- Rate limiting per user/tenant
- Response caching for performance
- Circuit breakers for resilience
- Full observability with OpenTelemetry

Performance characteristics:
- MCP tool calls: <100ms average
- REST endpoints: <50ms for cached responses
- SSE streaming: 10k+ concurrent connections
- Request batching: 10x throughput improvement

Security:
- Multi-tenant isolation
- Scoped API permissions
- Audit logging
- TLS everywhere

For more details, see: https://github.com/yourorg/uds/wiki/interface
*/
```

## Key Deliverables

1. **MCP Server** supporting all transports (stdio, HTTP, SSE)
2. **REST API** with full OpenAPI documentation
3. **CLI Tool** with interactive mode and progress visualization
4. **Client Libraries** in Go, TypeScript, Python
5. **SSE Streaming** for real-time progress updates
6. **Authentication & Authorization** with JWT and API keys
7. **Rate Limiting** and caching for performance
8. **95%+ test coverage** including integration tests
9. **Production-ready deployment** with Docker and monitoring

## Success Metrics

- MCP server works seamlessly with Copilot/Claude
- REST API handles 1000+ requests/second
- SSE supports 10k+ concurrent connections
- CLI provides excellent developer experience
- Zero-downtime deployments
- Complete API documentation
- Sub-100ms response times for most operations

This implementation provides a robust, scalable interface layer that makes UDS accessible to AI agents, applications, and developers alike.