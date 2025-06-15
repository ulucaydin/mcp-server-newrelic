package discovery

import (
	"context"
	"fmt"
	"os"
)

// InitializeEngine creates and starts a discovery engine
func InitializeEngine(ctx context.Context) (DiscoveryEngine, error) {
	// Load configuration
	config := DefaultConfig()
	
	// Override with environment variables if present
	if apiKey := os.Getenv("NEW_RELIC_API_KEY"); apiKey != "" {
		config.NRDB.APIKey = apiKey
	}
	if accountID := os.Getenv("NEW_RELIC_ACCOUNT_ID"); accountID != "" {
		config.NRDB.AccountID = accountID
	}
	
	// Create NRDB client
	nrdbClient, err := NewNRDBClient(config.NRDB)
	if err != nil {
		return nil, fmt.Errorf("failed to create NRDB client: %w", err)
	}
	
	// Create engine (use basic engine for now)
	engine := NewBasicEngine(*config, nrdbClient)
	
	// Start engine
	if err := engine.Start(ctx); err != nil {
		return nil, fmt.Errorf("failed to start engine: %w", err)
	}
	
	return engine, nil
}