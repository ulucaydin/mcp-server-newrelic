package mcp

import (
	"context"
	"fmt"
	"testing"
)

func TestToolRegistryConcurrency(t *testing.T) {
	registry := NewToolRegistry()
	
	// Test concurrent registration
	done := make(chan bool, 10)
	for i := 0; i < 10; i++ {
		go func(id int) {
			tool := Tool{
				Name:        fmt.Sprintf("concurrent.tool.%d", id),
				Description: "Test tool",
				Parameters:  ToolParameters{Type: "object"},
				Handler: func(ctx context.Context, params map[string]interface{}) (interface{}, error) {
					return nil, nil
				},
			}
			registry.Register(tool)
			done <- true
		}(i)
	}
	
	// Wait for all goroutines
	for i := 0; i < 10; i++ {
		<-done
	}
	
	// Verify all tools were registered
	tools := registry.List()
	if len(tools) != 10 {
		t.Errorf("Expected 10 tools, got %d", len(tools))
	}
}

func TestToolRegistryValidation(t *testing.T) {
	registry := NewToolRegistry()
	
	testCases := []struct {
		name        string
		tool        Tool
		expectError bool
		errorMsg    string
	}{
		{
			name: "Empty name",
			tool: Tool{
				Name:        "",
				Description: "Test",
				Parameters:  ToolParameters{Type: "object"},
				Handler:     func(ctx context.Context, params map[string]interface{}) (interface{}, error) { return nil, nil },
			},
			expectError: true,
			errorMsg:    "invalid tool : tool name is required",
		},
		{
			name: "No handler",
			tool: Tool{
				Name:        "test.tool",
				Description: "Test",
				Parameters:  ToolParameters{Type: "object"},
			},
			expectError: true,
			errorMsg:    "invalid tool test.tool: tool must have either a handler or stream handler",
		},
		{
			name: "Streaming without handler",
			tool: Tool{
				Name:        "test.stream",
				Description: "Test",
				Parameters:  ToolParameters{Type: "object"},
				Streaming:   true,
			},
			expectError: true,
			errorMsg:    "invalid tool test.stream: tool must have either a handler or stream handler",
		},
		{
			name: "Valid tool",
			tool: Tool{
				Name:        "valid.tool",
				Description: "Valid test tool",
				Parameters:  ToolParameters{Type: "object"},
				Handler:     func(ctx context.Context, params map[string]interface{}) (interface{}, error) { return nil, nil },
			},
			expectError: false,
		},
		{
			name: "Valid streaming tool",
			tool: Tool{
				Name:        "valid.stream",
				Description: "Valid streaming tool",
				Parameters:  ToolParameters{Type: "object"},
				Streaming:   true,
				StreamHandler: func(ctx context.Context, params map[string]interface{}, stream chan<- StreamChunk) {
					stream <- StreamChunk{Type: "data", Data: "test"}
					close(stream)
				},
			},
			expectError: false,
		},
	}
	
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			err := registry.Register(tc.tool)
			if tc.expectError {
				if err == nil {
					t.Fatal("Expected error but got none")
				}
				if err.Error() != tc.errorMsg {
					t.Errorf("Expected error '%s', got '%s'", tc.errorMsg, err.Error())
				}
			} else {
				if err != nil {
					t.Fatalf("Unexpected error: %v", err)
				}
			}
		})
	}
}