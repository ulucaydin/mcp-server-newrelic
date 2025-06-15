package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"sync/atomic"
	"time"
)

// ProtocolHandler implements the JSON-RPC 2.0 protocol for MCP
type ProtocolHandler struct {
	server    *Server
	requests  sync.Map // Track in-flight requests
	idCounter int64
}

// HandleMessage processes incoming JSON-RPC messages
func (h *ProtocolHandler) HandleMessage(ctx context.Context, message []byte) ([]byte, error) {
	// Parse request
	var req Request
	if err := json.Unmarshal(message, &req); err != nil {
		return h.errorResponse(nil, ParseError, "Parse error", err)
	}
	
	// Validate JSON-RPC version
	if req.Jsonrpc != "2.0" {
		return h.errorResponse(req.ID, InvalidRequest, "Invalid JSON-RPC version", nil)
	}
	
	// Route to appropriate handler
	switch req.Method {
	case "initialize":
		return h.handleInitialize(ctx, req)
	case "tools/list":
		return h.handleToolsList(ctx, req)
	case "tools/call":
		return h.handleToolCall(ctx, req)
	case "completion/complete":
		return h.handleCompletion(ctx, req)
	case "sessions/create":
		return h.handleSessionCreate(ctx, req)
	case "sessions/get":
		return h.handleSessionGet(ctx, req)
	default:
		return h.errorResponse(req.ID, MethodNotFound, "Method not found", nil)
	}
}

// OnError handles transport errors
func (h *ProtocolHandler) OnError(err error) {
	// Log error (implement proper logging)
	fmt.Printf("Protocol error: %v\n", err)
}

// handleInitialize handles the MCP initialization handshake
func (h *ProtocolHandler) handleInitialize(ctx context.Context, req Request) ([]byte, error) {
	// Return server capabilities
	result := map[string]interface{}{
		"protocolVersion": "2024-11-05",
		"capabilities": map[string]interface{}{
			"tools": map[string]interface{}{
				"listChanged": true,
			},
			"completion": map[string]interface{}{},
		},
		"serverInfo": h.server.GetInfo(),
	}
	
	return h.successResponse(req.ID, result)
}

// handleToolsList returns all available tools
func (h *ProtocolHandler) handleToolsList(ctx context.Context, req Request) ([]byte, error) {
	tools := h.server.tools.List()
	
	// Convert to MCP format
	toolSchemas := make([]map[string]interface{}, len(tools))
	for i, tool := range tools {
		toolSchemas[i] = map[string]interface{}{
			"name":        tool.Name,
			"description": tool.Description,
			"inputSchema": map[string]interface{}{
				"type":       tool.Parameters.Type,
				"properties": tool.Parameters.Properties,
				"required":   tool.Parameters.Required,
			},
		}
	}
	
	result := map[string]interface{}{
		"tools": toolSchemas,
	}
	
	return h.successResponse(req.ID, result)
}

// handleToolCall executes a tool
func (h *ProtocolHandler) handleToolCall(ctx context.Context, req Request) ([]byte, error) {
	var params ToolCallParams
	if err := json.Unmarshal(req.Params, &params); err != nil {
		return h.errorResponse(req.ID, InvalidParams, "Invalid parameters", err)
	}
	
	// Get tool from registry
	tool, exists := h.server.tools.Get(params.Name)
	if !exists {
		return h.errorResponse(req.ID, MethodNotFound, fmt.Sprintf("Tool '%s' not found", params.Name), nil)
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
	
	// Apply timeout
	ctx, cancel := context.WithTimeout(ctx, h.server.config.RequestTimeout)
	defer cancel()
	
	// Handle streaming if requested and supported
	if tool.Streaming && params.Stream {
		return h.handleStreamingToolCall(ctx, execCtx, params)
	}
	
	// Execute tool
	result, err := tool.Handler(ctx, params.Arguments)
	if err != nil {
		return h.errorResponse(req.ID, InternalError, fmt.Sprintf("Tool execution failed: %v", err), nil)
	}
	
	// Return success response
	return h.successResponse(req.ID, map[string]interface{}{
		"content": []map[string]interface{}{
			{
				"type": "text",
				"text": formatToolResult(result),
			},
		},
	})
}

// handleStreamingToolCall handles streaming tool execution
func (h *ProtocolHandler) handleStreamingToolCall(ctx context.Context, execCtx *ExecutionContext, params ToolCallParams) ([]byte, error) {
	// For HTTP/SSE transports, we'll return a streaming token
	// For stdio, we'll buffer and return the complete result
	
	if h.server.config.TransportType == TransportStdio {
		// Buffer streaming results for stdio
		stream := make(chan StreamChunk, 100)
		go execCtx.Tool.StreamHandler(ctx, params.Arguments, stream)
		
		var results []interface{}
		for chunk := range stream {
			if chunk.Error != nil {
				return h.errorResponse(execCtx.RequestID, InternalError, chunk.Error.Error(), nil)
			}
			if chunk.Type == "result" || chunk.Type == "complete" {
				results = append(results, chunk.Data)
			}
		}
		
		return h.successResponse(execCtx.RequestID, map[string]interface{}{
			"content": []map[string]interface{}{
				{
					"type": "text",
					"text": formatToolResult(results),
				},
			},
		})
	}
	
	// For HTTP/SSE, return a streaming token
	streamID := h.generateStreamID()
	
	// Start streaming in background
	go h.handleStreamingExecution(ctx, streamID, execCtx, params)
	
	return h.successResponse(execCtx.RequestID, map[string]interface{}{
		"stream": true,
		"streamId": streamID,
		"message": "Streaming response initiated",
	})
}

// handleCompletion provides completion suggestions
func (h *ProtocolHandler) handleCompletion(ctx context.Context, req Request) ([]byte, error) {
	var params struct {
		Ref struct {
			Type string `json:"type"`
			Name string `json:"name"`
		} `json:"ref"`
		Argument struct {
			Name  string `json:"name"`
			Value string `json:"value"`
		} `json:"argument"`
	}
	
	if err := json.Unmarshal(req.Params, &params); err != nil {
		return h.errorResponse(req.ID, InvalidParams, "Invalid parameters", err)
	}
	
	// Provide completions based on context
	var completions []map[string]interface{}
	
	if params.Ref.Type == "tool" {
		// Get tool-specific completions
		tool, exists := h.server.tools.Get(params.Ref.Name)
		if exists {
			completions = h.getToolCompletions(tool, params.Argument.Name, params.Argument.Value)
		}
	}
	
	result := map[string]interface{}{
		"completion": map[string]interface{}{
			"values": completions,
			"total": len(completions),
			"hasMore": false,
		},
	}
	
	return h.successResponse(req.ID, result)
}

// handleSessionCreate creates a new session
func (h *ProtocolHandler) handleSessionCreate(ctx context.Context, req Request) ([]byte, error) {
	session := h.server.sessions.Create()
	
	result := map[string]interface{}{
		"sessionId": session.ID,
		"createdAt": session.CreatedAt,
	}
	
	return h.successResponse(req.ID, result)
}

// handleSessionGet retrieves session information
func (h *ProtocolHandler) handleSessionGet(ctx context.Context, req Request) ([]byte, error) {
	var params struct {
		SessionID string `json:"sessionId"`
	}
	
	if err := json.Unmarshal(req.Params, &params); err != nil {
		return h.errorResponse(req.ID, InvalidParams, "Invalid parameters", err)
	}
	
	session, exists := h.server.sessions.Get(params.SessionID)
	if !exists {
		return h.errorResponse(req.ID, InvalidParams, "Session not found", nil)
	}
	
	result := map[string]interface{}{
		"session": session,
	}
	
	return h.successResponse(req.ID, result)
}

// Helper methods

func (h *ProtocolHandler) successResponse(id interface{}, result interface{}) ([]byte, error) {
	resp := Response{
		Jsonrpc: "2.0",
		Result:  result,
		ID:      id,
	}
	return json.Marshal(resp)
}

func (h *ProtocolHandler) errorResponse(id interface{}, code int, message string, data interface{}) ([]byte, error) {
	resp := Response{
		Jsonrpc: "2.0",
		Error: &Error{
			Code:    code,
			Message: message,
			Data:    data,
		},
		ID: id,
	}
	return json.Marshal(resp)
}

func (h *ProtocolHandler) generateStreamID() string {
	return fmt.Sprintf("stream_%d_%d", time.Now().UnixNano(), atomic.AddInt64(&h.idCounter, 1))
}

func (h *ProtocolHandler) handleStreamingExecution(ctx context.Context, streamID string, execCtx *ExecutionContext, params ToolCallParams) {
	stream := make(chan StreamChunk, 100)
	
	// Execute streaming handler
	go execCtx.Tool.StreamHandler(ctx, params.Arguments, stream)
	
	// Process stream chunks
	for chunk := range stream {
		// In a real implementation, this would send to SSE manager
		// For now, we'll just log
		fmt.Printf("Stream %s: %+v\n", streamID, chunk)
	}
}

func (h *ProtocolHandler) getToolCompletions(tool *Tool, argName, value string) []map[string]interface{} {
	completions := []map[string]interface{}{}
	
	// Get property definition
	prop, exists := tool.Parameters.Properties[argName]
	if !exists {
		return completions
	}
	
	// If enum is defined, return enum values
	if len(prop.Enum) > 0 {
		for _, enumVal := range prop.Enum {
			if value == "" || contains(enumVal, value) {
				completions = append(completions, map[string]interface{}{
					"value": enumVal,
					"label": enumVal,
				})
			}
		}
	}
	
	// Add type-specific completions
	switch prop.Type {
	case "boolean":
		completions = append(completions, 
			map[string]interface{}{"value": "true", "label": "true"},
			map[string]interface{}{"value": "false", "label": "false"},
		)
	}
	
	return completions
}

// Utility functions

func formatToolResult(result interface{}) string {
	// Convert result to readable text
	if str, ok := result.(string); ok {
		return str
	}
	
	bytes, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		return fmt.Sprintf("%v", result)
	}
	
	return string(bytes)
}

func contains(str, substr string) bool {
	return len(substr) > 0 && len(str) >= len(substr) && str[:len(substr)] == substr
}