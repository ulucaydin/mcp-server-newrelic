package mcp

import (
	"context"
	"encoding/json"
	"testing"
	"time"
)

func TestServerLifecycle(t *testing.T) {
	// Create server
	config := ServerConfig{
		TransportType:    TransportHTTP,
		HTTPHost:         "localhost",
		HTTPPort:         0, // Use random port
		RequestTimeout:   5 * time.Second,
		StreamingEnabled: true,
	}
	
	server := NewServer(config)
	
	// Create context
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	
	// Start server in goroutine
	errChan := make(chan error, 1)
	go func() {
		errChan <- server.Start(ctx)
	}()
	
	// Give server time to start
	time.Sleep(100 * time.Millisecond)
	
	// Stop server
	stopCtx, stopCancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer stopCancel()
	
	if err := server.Stop(stopCtx); err != nil {
		t.Fatalf("Failed to stop server: %v", err)
	}
	
	// Cancel context to stop Start()
	cancel()
	
	// Check for start errors
	select {
	case err := <-errChan:
		if err != nil && err != context.Canceled {
			t.Fatalf("Server start error: %v", err)
		}
	case <-time.After(1 * time.Second):
		t.Fatal("Server start timeout")
	}
}

func TestToolRegistry(t *testing.T) {
	registry := NewToolRegistry()
	
	// Test registration
	tool := Tool{
		Name:        "test.tool",
		Description: "Test tool",
		Parameters: ToolParameters{
			Type: "object",
			Properties: map[string]Property{
				"param1": {
					Type:        "string",
					Description: "Test parameter",
				},
			},
		},
		Handler: func(ctx context.Context, params map[string]interface{}) (interface{}, error) {
			return map[string]string{"result": "success"}, nil
		},
	}
	
	if err := registry.Register(tool); err != nil {
		t.Fatalf("Failed to register tool: %v", err)
	}
	
	// Test retrieval
	retrieved, exists := registry.Get("test.tool")
	if !exists {
		t.Fatal("Tool not found after registration")
	}
	
	if retrieved.Name != tool.Name {
		t.Errorf("Expected tool name %s, got %s", tool.Name, retrieved.Name)
	}
	
	// Test duplicate registration
	if err := registry.Register(tool); err == nil {
		t.Fatal("Expected error for duplicate registration")
	}
	
	// Test list
	tools := registry.List()
	if len(tools) != 1 {
		t.Errorf("Expected 1 tool, got %d", len(tools))
	}
	
	// Test unregister
	if err := registry.Unregister("test.tool"); err != nil {
		t.Fatalf("Failed to unregister tool: %v", err)
	}
	
	_, exists = registry.Get("test.tool")
	if exists {
		t.Fatal("Tool found after unregistration")
	}
}

func TestProtocolHandler(t *testing.T) {
	// Create server with mock transport
	server := &Server{
		tools:     NewToolRegistry(),
		sessions:  NewSessionManager(),
		config: ServerConfig{
			RequestTimeout: 5 * time.Second,
		},
	}
	
	handler := &ProtocolHandler{
		server: server,
	}
	
	// Register test tool
	server.tools.Register(Tool{
		Name:        "test.echo",
		Description: "Echo test",
		Parameters: ToolParameters{
			Type: "object",
			Properties: map[string]Property{
				"message": {
					Type:        "string",
					Description: "Message to echo",
				},
			},
		},
		Handler: func(ctx context.Context, params map[string]interface{}) (interface{}, error) {
			message, _ := params["message"].(string)
			return map[string]string{"echo": message}, nil
		},
	})
	
	// Test initialize
	t.Run("Initialize", func(t *testing.T) {
		req := Request{
			Jsonrpc: "2.0",
			Method:  "initialize",
			ID:      1,
		}
		
		reqBytes, _ := json.Marshal(req)
		respBytes, err := handler.HandleMessage(context.Background(), reqBytes)
		if err != nil {
			t.Fatalf("Handle message error: %v", err)
		}
		
		var resp Response
		if err := json.Unmarshal(respBytes, &resp); err != nil {
			t.Fatalf("Unmarshal response error: %v", err)
		}
		
		if resp.Error != nil {
			t.Fatalf("Response error: %v", resp.Error)
		}
		
		if resp.Result == nil {
			t.Fatal("Expected result")
		}
	})
	
	// Test tools/list
	t.Run("ToolsList", func(t *testing.T) {
		req := Request{
			Jsonrpc: "2.0",
			Method:  "tools/list",
			ID:      2,
		}
		
		reqBytes, _ := json.Marshal(req)
		respBytes, err := handler.HandleMessage(context.Background(), reqBytes)
		if err != nil {
			t.Fatalf("Handle message error: %v", err)
		}
		
		var resp Response
		if err := json.Unmarshal(respBytes, &resp); err != nil {
			t.Fatalf("Unmarshal response error: %v", err)
		}
		
		if resp.Error != nil {
			t.Fatalf("Response error: %v", resp.Error)
		}
		
		result, ok := resp.Result.(map[string]interface{})
		if !ok {
			t.Fatal("Invalid result type")
		}
		
		tools, ok := result["tools"].([]interface{})
		if !ok {
			t.Fatal("Invalid tools type")
		}
		
		if len(tools) != 1 {
			t.Errorf("Expected 1 tool, got %d", len(tools))
		}
	})
	
	// Test tools/call
	t.Run("ToolCall", func(t *testing.T) {
		params := ToolCallParams{
			Name: "test.echo",
			Arguments: map[string]interface{}{
				"message": "hello world",
			},
		}
		
		paramsBytes, _ := json.Marshal(params)
		
		req := Request{
			Jsonrpc: "2.0",
			Method:  "tools/call",
			Params:  json.RawMessage(paramsBytes),
			ID:      3,
		}
		
		reqBytes, _ := json.Marshal(req)
		respBytes, err := handler.HandleMessage(context.Background(), reqBytes)
		if err != nil {
			t.Fatalf("Handle message error: %v", err)
		}
		
		var resp Response
		if err := json.Unmarshal(respBytes, &resp); err != nil {
			t.Fatalf("Unmarshal response error: %v", err)
		}
		
		if resp.Error != nil {
			t.Fatalf("Response error: %v", resp.Error)
		}
		
		if resp.Result == nil {
			t.Fatal("Expected result")
		}
	})
}

func TestSessionManager(t *testing.T) {
	manager := NewSessionManager()
	
	// Create session
	session := manager.Create()
	if session.ID == "" {
		t.Fatal("Empty session ID")
	}
	
	// Get session
	retrieved, exists := manager.Get(session.ID)
	if !exists {
		t.Fatal("Session not found")
	}
	
	if retrieved.ID != session.ID {
		t.Errorf("Session ID mismatch: expected %s, got %s", session.ID, retrieved.ID)
	}
	
	// Update session
	session.Context["test"] = "value"
	if err := manager.Update(session); err != nil {
		t.Fatalf("Failed to update session: %v", err)
	}
	
	// Delete session
	if err := manager.Delete(session.ID); err != nil {
		t.Fatalf("Failed to delete session: %v", err)
	}
	
	_, exists = manager.Get(session.ID)
	if exists {
		t.Fatal("Session found after deletion")
	}
}