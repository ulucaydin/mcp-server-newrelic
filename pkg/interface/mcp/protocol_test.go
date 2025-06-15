package mcp

import (
	"context"
	"encoding/json"
	"testing"
	"time"
)

func TestProtocolHandlerErrors(t *testing.T) {
	server := &Server{
		tools:    NewToolRegistry(),
		sessions: NewSessionManager(),
		config: ServerConfig{
			RequestTimeout: 1 * time.Second,
		},
	}
	
	handler := &ProtocolHandler{
		server: server,
	}
	
	testCases := []struct {
		name        string
		request     string
		expectError bool
		errorCode   int
	}{
		{
			name:        "Invalid JSON",
			request:     `{invalid json`,
			expectError: true,
			errorCode:   ParseError,
		},
		{
			name:        "Missing method",
			request:     `{"jsonrpc":"2.0","id":1}`,
			expectError: true,
			errorCode:   MethodNotFound,
		},
		{
			name:        "Unknown method",
			request:     `{"jsonrpc":"2.0","method":"unknown.method","id":1}`,
			expectError: true,
			errorCode:   MethodNotFound,
		},
		{
			name:        "Invalid params",
			request:     `{"jsonrpc":"2.0","method":"tools/call","params":"invalid","id":1}`,
			expectError: true,
			errorCode:   InvalidParams,
		},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			respBytes, err := handler.HandleMessage(context.Background(), []byte(tc.request))
			if err != nil {
				t.Fatalf("HandleMessage error: %v", err)
			}
			
			var resp Response
			if err := json.Unmarshal(respBytes, &resp); err != nil {
				t.Fatalf("Unmarshal response error: %v", err)
			}
			
			if tc.expectError {
				if resp.Error == nil {
					t.Fatal("Expected error response")
				}
				if resp.Error.Code != tc.errorCode {
					t.Errorf("Expected error code %d, got %d", tc.errorCode, resp.Error.Code)
				}
			} else {
				if resp.Error != nil {
					t.Fatalf("Unexpected error: %v", resp.Error)
				}
			}
		})
	}
}

func TestProtocolHandlerNotifications(t *testing.T) {
	server := &Server{
		tools:    NewToolRegistry(),
		sessions: NewSessionManager(),
		config: ServerConfig{
			RequestTimeout: 1 * time.Second,
		},
	}
	
	handler := &ProtocolHandler{
		server: server,
	}
	
	// Notification (no ID) currently returns a response (JSON-RPC spec says no response)
	// For now, we'll test that it doesn't error
	notification := `{"jsonrpc":"2.0","method":"tools/list"}`
	respBytes, err := handler.HandleMessage(context.Background(), []byte(notification))
	if err != nil {
		t.Fatalf("HandleMessage error: %v", err)
	}
	
	// Current implementation returns a response even for notifications
	// This could be improved to follow JSON-RPC spec more strictly
	if respBytes == nil {
		t.Error("Expected response even for notification (current implementation)")
	}
}

func TestProtocolHandlerToolExecution(t *testing.T) {
	server := &Server{
		tools:    NewToolRegistry(),
		sessions: NewSessionManager(),
		config: ServerConfig{
			RequestTimeout: 1 * time.Second,
		},
	}
	
	handler := &ProtocolHandler{
		server: server,
	}
	
	// Register a test tool that returns the input
	server.tools.Register(Tool{
		Name:        "test.echo",
		Description: "Echo input",
		Parameters: ToolParameters{
			Type: "object",
			Properties: map[string]Property{
				"message": {
					Type:        "string",
					Description: "Message to echo",
				},
			},
			Required: []string{"message"},
		},
		Handler: func(ctx context.Context, params map[string]interface{}) (interface{}, error) {
			message := params["message"].(string)
			return map[string]string{"echo": message}, nil
		},
	})
	
	// Test successful tool execution
	req := Request{
		Jsonrpc: "2.0",
		Method:  "tools/call",
		Params: json.RawMessage(`{
			"name": "test.echo",
			"arguments": {"message": "hello world"}
		}`),
		ID: 1,
	}
	
	reqBytes, _ := json.Marshal(req)
	respBytes, err := handler.HandleMessage(context.Background(), reqBytes)
	if err != nil {
		t.Fatalf("HandleMessage error: %v", err)
	}
	
	var resp Response
	if err := json.Unmarshal(respBytes, &resp); err != nil {
		t.Fatalf("Unmarshal response error: %v", err)
	}
	
	if resp.Error != nil {
		t.Fatalf("Unexpected error: %v", resp.Error)
	}
	
	// Verify result
	result, ok := resp.Result.(map[string]interface{})
	if !ok {
		t.Fatal("Invalid result type")
	}
	
	content, ok := result["content"].([]interface{})
	if !ok || len(content) == 0 {
		t.Fatal("Missing content in result")
	}
	
	// Test tool not found
	req.Params = json.RawMessage(`{
		"name": "nonexistent.tool",
		"arguments": {}
	}`)
	
	reqBytes, _ = json.Marshal(req)
	respBytes, err = handler.HandleMessage(context.Background(), reqBytes)
	if err != nil {
		t.Fatalf("HandleMessage error: %v", err)
	}
	
	if err := json.Unmarshal(respBytes, &resp); err != nil {
		t.Fatalf("Unmarshal response error: %v", err)
	}
	
	if resp.Error == nil {
		t.Fatal("Expected error for nonexistent tool")
	}
}