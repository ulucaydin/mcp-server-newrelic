package main

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/client"
)

func main() {
	// Create client with retry logic
	c, err := client.NewClient(client.Config{
		BaseURL:   "http://localhost:8080/api/v1",
		Timeout:   30 * time.Second,
		RetryMax:  3,
		RetryWait: 1 * time.Second,
	})
	if err != nil {
		log.Fatal(err)
	}

	ctx := context.Background()

	// Check health
	fmt.Println("=== Checking API Health ===")
	health, err := c.Health(ctx)
	if err != nil {
		log.Printf("Health check failed: %v", err)
	} else {
		fmt.Printf("Status: %s\n", health.Status)
		fmt.Printf("Version: %s\n", health.Version)
		fmt.Printf("Uptime: %s\n", health.Uptime)
	}

	// List schemas
	fmt.Println("\n=== Listing Schemas ===")
	schemas, err := c.Discovery.ListSchemas(ctx, &client.ListSchemasOptions{
		MaxSchemas:      10,
		IncludeMetadata: true,
	})
	if err != nil {
		log.Printf("Failed to list schemas: %v", err)
	} else {
		for _, schema := range schemas.Schemas {
			fmt.Printf("- %s: %d records (quality: %.2f)\n", 
				schema.Name, schema.RecordCount, schema.Quality.OverallScore)
		}
		if schemas.Metadata != nil {
			fmt.Printf("\nTotal schemas: %d\n", schemas.Metadata.TotalSchemas)
			fmt.Printf("Execution time: %s\n", schemas.Metadata.ExecutionTime)
		}
	}

	// Get detailed schema profile
	fmt.Println("\n=== Schema Profile: Transaction ===")
	profile, err := c.Discovery.GetSchemaProfile(ctx, "Transaction", &client.ProfileSchemaOptions{
		Depth: "full",
	})
	if err != nil {
		log.Printf("Failed to get schema profile: %v", err)
	} else {
		fmt.Printf("Event Type: %s\n", profile.EventType)
		fmt.Printf("Record Count: %d\n", profile.RecordCount)
		fmt.Printf("Attributes: %d\n", len(profile.Attributes))
		for _, attr := range profile.Attributes {
			fmt.Printf("  - %s (%s): null ratio %.2f%%\n", 
				attr.Name, attr.DataType, attr.NullRatio*100)
		}
	}

	// Find relationships
	fmt.Println("\n=== Finding Relationships ===")
	relationships, err := c.Discovery.FindRelationships(ctx, 
		[]string{"Transaction", "PageView"}, 
		&client.FindRelationshipsOptions{
			MinConfidence: 0.7,
		})
	if err != nil {
		log.Printf("Failed to find relationships: %v", err)
	} else {
		for _, rel := range relationships {
			fmt.Printf("- %s relationship: %s.%s <-> %s.%s (confidence: %.2f)\n",
				rel.Type, rel.SourceSchema, rel.SourceAttribute,
				rel.TargetSchema, rel.TargetAttribute, rel.Confidence)
		}
	}

	// Assess quality
	fmt.Println("\n=== Quality Assessment: Transaction ===")
	quality, err := c.Discovery.AssessQuality(ctx, "Transaction", &client.AssessQualityOptions{
		TimeRange: "24h",
	})
	if err != nil {
		log.Printf("Failed to assess quality: %v", err)
	} else {
		fmt.Printf("Overall Score: %.2f\n", quality.Metrics.OverallScore)
		fmt.Printf("Completeness: %.2f\n", quality.Metrics.Completeness)
		fmt.Printf("Consistency: %.2f\n", quality.Metrics.Consistency)
		
		if len(quality.Issues) > 0 {
			fmt.Println("\nIssues:")
			for _, issue := range quality.Issues {
				fmt.Printf("  - [%s] %s: %s\n", issue.Severity, issue.Type, issue.Description)
			}
		}
		
		if len(quality.Recommendations) > 0 {
			fmt.Println("\nRecommendations:")
			for _, rec := range quality.Recommendations {
				fmt.Printf("  - [%s] %s\n", rec.Priority, rec.Description)
			}
		}
	}

	// Pattern analysis (will fail as not implemented)
	fmt.Println("\n=== Pattern Analysis ===")
	patterns, err := c.Patterns.AnalyzePatterns(ctx, &client.PatternAnalysisRequest{
		EventType: "Transaction",
		TimeRange: "24h",
	})
	if err != nil {
		fmt.Printf("Pattern analysis not available: %v\n", err)
	} else {
		fmt.Printf("Found %d patterns\n", len(patterns.Patterns))
	}

	// Query generation (will fail as not implemented)
	fmt.Println("\n=== Query Generation ===")
	query, err := c.Query.GenerateQuery(ctx, 
		"show me the average transaction duration by application", 
		&client.QueryContext{
			Schemas:   []string{"Transaction"},
			TimeRange: "1h",
		})
	if err != nil {
		fmt.Printf("Query generation not available: %v\n", err)
	} else {
		fmt.Printf("Generated NRQL: %s\n", query.NRQL)
		fmt.Printf("Explanation: %s\n", query.Explanation)
	}
}