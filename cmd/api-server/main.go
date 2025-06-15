package main

import (
	"context"
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/interface/api"
)

func main() {
	// Parse command line flags
	var (
		host            = flag.String("host", "localhost", "API server host")
		port            = flag.Int("port", 8080, "API server port")
		enableCORS      = flag.Bool("cors", true, "Enable CORS")
		enableSwagger   = flag.Bool("swagger", true, "Enable Swagger UI")
		rateLimit       = flag.Int("rate-limit", 100, "Rate limit per minute (0 to disable)")
		maxRequestSize  = flag.Int64("max-request-size", 1024*1024, "Maximum request size in bytes")
		readTimeout     = flag.Duration("read-timeout", 30*time.Second, "Read timeout")
		writeTimeout    = flag.Duration("write-timeout", 30*time.Second, "Write timeout")
	)

	flag.Parse()

	// Create API configuration
	config := api.Config{
		Host:            *host,
		Port:            *port,
		ReadTimeout:     *readTimeout,
		WriteTimeout:    *writeTimeout,
		MaxRequestSize:  *maxRequestSize,
		EnableCORS:      *enableCORS,
		EnableSwagger:   *enableSwagger,
		RateLimitPerMin: *rateLimit,
	}

	// Create handler
	handler := api.NewHandler()

	// NOTE: Discovery engine from Track 1 will be initialized here when ready
	// handler.SetDiscoveryEngine(discoveryEngine)

	// Create and start server
	server := api.NewServer(config, handler)

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
	log.Printf("Starting API server on %s:%d", *host, *port)
	if *enableSwagger {
		log.Printf("Swagger UI available at http://%s:%d/swagger/", *host, *port)
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