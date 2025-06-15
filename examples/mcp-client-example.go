package main

import (
	"bufio"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"log"
	"os"
)

// Simple MCP client example demonstrating stdio transport communication

type Request struct {
	Jsonrpc string                 `json:"jsonrpc"`
	Method  string                 `json:"method"`
	Params  map[string]interface{} `json:"params,omitempty"`
	ID      interface{}            `json:"id"`
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

func main() {
	// Initialize connection
	fmt.Fprintln(os.Stderr, "Initializing MCP connection...")
	
	// Send initialize request
	initReq := Request{
		Jsonrpc: "2.0",
		Method:  "initialize",
		ID:      1,
	}
	
	resp, err := sendRequest(initReq)
	if err != nil {
		log.Fatalf("Failed to initialize: %v", err)
	}
	
	fmt.Fprintf(os.Stderr, "Initialized: %+v\n", resp.Result)
	
	// List available tools
	toolsReq := Request{
		Jsonrpc: "2.0",
		Method:  "tools/list",
		ID:      2,
	}
	
	resp, err = sendRequest(toolsReq)
	if err != nil {
		log.Fatalf("Failed to list tools: %v", err)
	}
	
	fmt.Fprintln(os.Stderr, "\nAvailable tools:")
	if result, ok := resp.Result.(map[string]interface{}); ok {
		if tools, ok := result["tools"].([]interface{}); ok {
			for _, tool := range tools {
				if t, ok := tool.(map[string]interface{}); ok {
					fmt.Fprintf(os.Stderr, "- %s: %s\n", t["name"], t["description"])
				}
			}
		}
	}
	
	// Call a tool
	callReq := Request{
		Jsonrpc: "2.0",
		Method:  "tools/call",
		Params: map[string]interface{}{
			"name": "discovery.list_schemas",
			"arguments": map[string]interface{}{
				"filter": map[string]interface{}{
					"max_schemas": 5,
				},
			},
		},
		ID: 3,
	}
	
	resp, err = sendRequest(callReq)
	if err != nil {
		log.Fatalf("Failed to call tool: %v", err)
	}
	
	fmt.Fprintf(os.Stderr, "\nTool result: %+v\n", resp.Result)
}

func sendRequest(req Request) (*Response, error) {
	// Marshal request
	data, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}
	
	// Write length header
	length := uint32(len(data))
	if err := binary.Write(os.Stdout, binary.BigEndian, length); err != nil {
		return nil, fmt.Errorf("failed to write length: %w", err)
	}
	
	// Write message
	if _, err := os.Stdout.Write(data); err != nil {
		return nil, fmt.Errorf("failed to write message: %w", err)
	}
	
	// Read response
	reader := bufio.NewReader(os.Stdin)
	
	// Read length header
	var respLength uint32
	if err := binary.Read(reader, binary.BigEndian, &respLength); err != nil {
		return nil, fmt.Errorf("failed to read response length: %w", err)
	}
	
	// Read message
	respData := make([]byte, respLength)
	if _, err := reader.Read(respData); err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}
	
	// Unmarshal response
	var resp Response
	if err := json.Unmarshal(respData, &resp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}
	
	if resp.Error != nil {
		return nil, fmt.Errorf("server error: %s (code: %d)", resp.Error.Message, resp.Error.Code)
	}
	
	return &resp, nil
}