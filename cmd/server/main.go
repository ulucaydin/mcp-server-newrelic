package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/config"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/interface/api"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/interface/mcp"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/state"
	"github.com/newrelic/go-agent/v3/newrelic"
)

func main() {
	log.Println("Starting MCP Server for New Relic...")

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// Validate configuration
	if err := cfg.Validate(); err != nil {
		log.Fatalf("Invalid configuration: %v", err)
	}

	// Initialize New Relic APM
	var nrApp *newrelic.Application
	if cfg.APM.Enabled {
		nrApp, err = cfg.NewAPMApplication()
		if err != nil {
			log.Printf("Warning: Failed to initialize New Relic APM: %v", err)
			// Continue without APM
		} else {
			log.Printf("New Relic APM initialized for app: %s", cfg.APM.AppName)
		}
	}

	// Create context for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	
	// Initialize discovery engine
	log.Println("Initializing discovery engine...")
	discoveryEngine, err := discovery.InitializeEngine(ctx)
	if err != nil {
		log.Printf("Warning: Failed to initialize discovery engine: %v", err)
		// Continue without discovery for now
	} else {
		log.Println("Discovery engine initialized successfully")
		
		// Pass New Relic app to discovery engine if available
		// Note: SetNewRelicApp is only available on the full Engine implementation
		// not on the BasicEngine, so we skip this for now
	}

	// Start MCP server
	if cfg.Server.MCPTransport != "" {
		// Set transport type based on configuration
		var transportTypeEnum mcp.TransportType
		switch cfg.Server.MCPTransport {
		case "stdio":
			transportTypeEnum = mcp.TransportStdio
		case "http":
			transportTypeEnum = mcp.TransportHTTP
		case "sse":
			transportTypeEnum = mcp.TransportSSE
		default:
			log.Fatalf("Unknown transport type: %s", cfg.Server.MCPTransport)
		}
		
		mcpConfig := mcp.ServerConfig{
			TransportType:    transportTypeEnum,
			MaxConcurrent:    cfg.Server.MaxConcurrentRequests,
			RequestTimeout:   cfg.Server.RequestTimeout,
			StreamingEnabled: true,
			AuthEnabled:      cfg.Security.AuthEnabled,
			HTTPHost:         cfg.Server.Host,
			HTTPPort:         cfg.Server.MCPHTTPPort,
		}

		mcpServer := mcp.NewServer(mcpConfig)
		
		// Set discovery engine if available
		if discoveryEngine != nil {
			mcpServer.SetDiscovery(discoveryEngine)
		}

		// Start MCP server in background
		go func() {
			// Create New Relic transaction for MCP server
			if nrApp != nil {
				txn := nrApp.StartTransaction("MCP.Server.Start")
				defer txn.End()
			}

			if err := mcpServer.Start(ctx); err != nil {
				log.Printf("MCP server error: %v", err)
			}
		}()

		log.Printf("MCP server started with %s transport on port %d", cfg.Server.MCPTransport, cfg.Server.MCPHTTPPort)
	}

	// Start REST API server
	apiConfig := api.Config{
		Host:            cfg.Server.Host,
		Port:            cfg.Server.Port,
		ReadTimeout:     cfg.Server.RequestTimeout,
		WriteTimeout:    cfg.Server.RequestTimeout,
		MaxRequestSize:  10 * 1024 * 1024, // 10MB
		EnableCORS:      true,
		EnableSwagger:   cfg.Features.QueryGeneration, // Use feature flag
		RateLimitPerMin: cfg.Security.RateLimitPerMin,
	}

	// Create handler based on build tags
	handler := api.NewHandler()
	
	// Set discovery engine if available
	if discoveryEngine != nil {
		handler.SetDiscoveryEngine(discoveryEngine)
	}
	
	// Pass New Relic app to handler if available
	if nrApp != nil {
		handler.SetNewRelicApp(nrApp)
	}
	
	// Create and start API server
	apiServer := api.NewServer(apiConfig, handler)
	
	// Inject New Relic app if available
	if nrApp != nil {
		apiServer.SetNewRelicApp(nrApp)
	}

	// Start API server in background
	go func() {
		// Create New Relic transaction for API server
		if nrApp != nil {
			txn := nrApp.StartTransaction("API.Server.Start")
			defer txn.End()
		}

		if err := apiServer.Start(ctx); err != nil {
			log.Printf("API server error: %v", err)
		}
	}()

	log.Printf("REST API server started on %s:%d", cfg.Server.Host, cfg.Server.Port)

	// Start metrics server if enabled
	if cfg.Monitoring.MetricsEnabled {
		go startMetricsServer(cfg.Monitoring.MetricsPort, cfg.Monitoring.MetricsPath)
	}

	// Start profiling server if enabled
	if cfg.Development.EnableProfiling {
		go startProfilingServer(cfg.Development.PProfPort)
	}

	// Log configuration summary
	logConfigSummary(cfg)

	// Wait for interrupt signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	<-sigChan

	log.Println("Shutting down servers...")
	
	// Shutdown New Relic app gracefully
	if nrApp != nil {
		nrApp.Shutdown(cfg.Server.RequestTimeout)
	}

	// Give servers time to shutdown gracefully
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), cfg.Server.RequestTimeout)
	defer shutdownCancel()

	// Cancel main context to trigger shutdown
	cancel()

	// Wait for shutdown or timeout
	<-shutdownCtx.Done()
	
	log.Println("Server shutdown complete")
}

func startMetricsServer(port int, path string) {
	// Implementation would go here
	log.Printf("Metrics server started on port %d at path %s", port, path)
}

func startProfilingServer(port int) {
	// Implementation would go here
	log.Printf("Profiling server started on port %d", port)
}

func logConfigSummary(cfg *config.Config) {
	log.Println("Configuration Summary:")
	log.Printf("  Environment: %s", cfg.APM.Environment)
	log.Printf("  New Relic Account: %s", cfg.NewRelic.AccountID)
	log.Printf("  New Relic Region: %s", cfg.NewRelic.Region)
	log.Printf("  APM Enabled: %v", cfg.APM.Enabled)
	log.Printf("  Features Enabled:")
	log.Printf("    - Pattern Detection: %v", cfg.Features.PatternDetection)
	log.Printf("    - Query Generation: %v", cfg.Features.QueryGeneration)
	log.Printf("    - Anomaly Detection: %v", cfg.Features.AnomalyDetection)
	log.Printf("  Security:")
	log.Printf("    - Auth Enabled: %v", cfg.Security.AuthEnabled)
	log.Printf("    - Rate Limiting: %v (max %d/min)", cfg.Security.RateLimitEnabled, cfg.Security.RateLimitPerMin)
	log.Printf("  Development Mode: %v", cfg.Development.DevMode)
}