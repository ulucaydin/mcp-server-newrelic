package main

import (
	"context"
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/interface/mcp"
)

func main() {
	// Parse command line flags
	var (
		transport = flag.String("transport", "stdio", "Transport type: stdio, http, sse")
		httpHost  = flag.String("host", "localhost", "HTTP server host")
		httpPort  = flag.Int("port", 9090, "HTTP server port")
		timeout   = flag.Duration("timeout", 30*time.Second, "Request timeout")
		debug     = flag.Bool("debug", false, "Enable debug logging")
	)
	
	flag.Parse()
	
	// Validate transport
	transportType := mcp.TransportType(*transport)
	switch transportType {
	case mcp.TransportStdio, mcp.TransportHTTP, mcp.TransportSSE:
		// Valid
	default:
		log.Fatalf("Invalid transport type: %s", *transport)
	}
	
	// Create server configuration
	config := mcp.ServerConfig{
		TransportType:    transportType,
		HTTPHost:         *httpHost,
		HTTPPort:         *httpPort,
		RequestTimeout:   *timeout,
		StreamingEnabled: true,
		AuthEnabled:      false, // TODO: Enable in production
	}
	
	// Create MCP server
	server := mcp.NewServer(config)
	
	// NOTE: Discovery engine from Track 1 will be initialized here when ready
	// For now, the MCP server will run with limited functionality
	
	// Setup context with cancellation
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	
	// Handle shutdown signals
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	
	go func() {
		<-sigChan
		log.Println("Shutdown signal received")
		cancel()
	}()
	
	// Start server
	log.Printf("Starting MCP server with %s transport", transportType)
	if transportType == mcp.TransportHTTP || transportType == mcp.TransportSSE {
		log.Printf("Listening on %s:%d", *httpHost, *httpPort)
	}
	
	if err := server.Start(ctx); err != nil {
		log.Fatalf("Server error: %v", err)
	}
	
	// Graceful shutdown
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer shutdownCancel()
	
	if err := server.Stop(shutdownCtx); err != nil {
		log.Printf("Shutdown error: %v", err)
	}
	
	log.Println("Server stopped")
}