package mcp

import (
	"fmt"
	"sync"
)

// toolRegistry implements the ToolRegistry interface
type toolRegistry struct {
	mu    sync.RWMutex
	tools map[string]*Tool
}

// NewToolRegistry creates a new tool registry
func NewToolRegistry() ToolRegistry {
	return &toolRegistry{
		tools: make(map[string]*Tool),
	}
}

// Register adds a new tool to the registry
func (r *toolRegistry) Register(tool Tool) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	
	if _, exists := r.tools[tool.Name]; exists {
		return fmt.Errorf("tool %s already registered", tool.Name)
	}
	
	// Validate tool
	if err := validateTool(&tool); err != nil {
		return fmt.Errorf("invalid tool %s: %w", tool.Name, err)
	}
	
	r.tools[tool.Name] = &tool
	return nil
}

// Get retrieves a tool by name
func (r *toolRegistry) Get(name string) (*Tool, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	
	tool, exists := r.tools[name]
	return tool, exists
}

// List returns all registered tools
func (r *toolRegistry) List() []Tool {
	r.mu.RLock()
	defer r.mu.RUnlock()
	
	tools := make([]Tool, 0, len(r.tools))
	for _, tool := range r.tools {
		tools = append(tools, *tool)
	}
	return tools
}

// Unregister removes a tool from the registry
func (r *toolRegistry) Unregister(name string) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	
	if _, exists := r.tools[name]; !exists {
		return fmt.Errorf("tool %s not found", name)
	}
	
	delete(r.tools, name)
	return nil
}

// validateTool ensures a tool is properly configured
func validateTool(tool *Tool) error {
	if tool.Name == "" {
		return fmt.Errorf("tool name is required")
	}
	
	if tool.Description == "" {
		return fmt.Errorf("tool description is required")
	}
	
	if tool.Handler == nil && tool.StreamHandler == nil {
		return fmt.Errorf("tool must have either a handler or stream handler")
	}
	
	if tool.Streaming && tool.StreamHandler == nil {
		return fmt.Errorf("streaming tool must have a stream handler")
	}
	
	if tool.Parameters.Type == "" {
		tool.Parameters.Type = "object"
	}
	
	if tool.Parameters.Properties == nil {
		tool.Parameters.Properties = make(map[string]Property)
	}
	
	return nil
}