package mcp

import (
	"context"
	"encoding/json"
	"time"
)

// Transport types
type TransportType string

const (
	TransportStdio TransportType = "stdio"
	TransportHTTP  TransportType = "http"
	TransportSSE   TransportType = "sse"
)

// JSON-RPC 2.0 types
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

// Tool definitions
type Tool struct {
	Name         string
	Description  string
	Parameters   ToolParameters
	Handler      ToolHandler
	Streaming    bool
	StreamHandler StreamingToolHandler
}

type ToolParameters struct {
	Type       string               `json:"type"`
	Properties map[string]Property  `json:"properties"`
	Required   []string             `json:"required,omitempty"`
}

type Property struct {
	Type        string      `json:"type"`
	Description string      `json:"description"`
	Default     interface{} `json:"default,omitempty"`
	Enum        []string    `json:"enum,omitempty"`
	Items       *Property   `json:"items,omitempty"`
}

// Tool execution types
type ToolHandler func(ctx context.Context, params map[string]interface{}) (interface{}, error)
type StreamingToolHandler func(ctx context.Context, params map[string]interface{}, stream chan<- StreamChunk)

type ToolCallParams struct {
	Name      string                 `json:"name"`
	Arguments map[string]interface{} `json:"arguments"`
	Stream    bool                   `json:"stream,omitempty"`
}

type ExecutionContext struct {
	RequestID interface{}
	Tool      *Tool
	StartTime time.Time
}

// Streaming types
type StreamChunk struct {
	Type  string      `json:"type"`
	Data  interface{} `json:"data"`
	Error error       `json:"error,omitempty"`
}

type StreamingResponse struct {
	ID      interface{}
	Channel chan StreamChunk
}

// Transport interface
type Transport interface {
	Start(ctx context.Context, handler MessageHandler) error
	Send(message []byte) error
	Close() error
}

type MessageHandler interface {
	HandleMessage(ctx context.Context, message []byte) ([]byte, error)
	OnError(error)
}

// Server configuration
type ServerConfig struct {
	TransportType    TransportType
	MaxConcurrent    int
	RequestTimeout   time.Duration
	StreamingEnabled bool
	AuthEnabled      bool
	HTTPPort         int
	HTTPHost         string
}

// Tool registry interface
type ToolRegistry interface {
	Register(tool Tool) error
	Get(name string) (*Tool, bool)
	List() []Tool
	Unregister(name string) error
}

// Session management
type Session struct {
	ID        string
	CreatedAt time.Time
	LastUsed  time.Time
	Context   map[string]interface{}
}

type SessionManager interface {
	Create() *Session
	Get(id string) (*Session, bool)
	Update(session *Session) error
	Delete(id string) error
	Cleanup() error
}