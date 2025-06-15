package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/spf13/cobra"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
)

var (
	// Global flags
	configFile string
	outputFormat string
	verbose bool
	
	// Discovery flags
	maxSchemas int
	minRecords int
	eventTypes []string
	keywords []string
	purpose string
	domain string
	
	// Profile flags
	profileDepth string
)

var rootCmd = &cobra.Command{
	Use:   "uds-discovery",
	Short: "Universal Data Synthesizer - Discovery Core CLI",
	Long: `UDS Discovery Core is a powerful schema discovery engine for New Relic data.
It provides intelligent schema discovery, pattern detection, relationship mining,
and quality assessment capabilities.`,
}

var discoverCmd = &cobra.Command{
	Use:   "discover",
	Short: "Discover schemas from New Relic data",
	Long:  `Discover schemas with optional intelligent filtering based on keywords, purpose, and domain.`,
	Run:   runDiscover,
}

var profileCmd = &cobra.Command{
	Use:   "profile [event-type]",
	Short: "Profile a specific schema in detail",
	Args:  cobra.ExactArgs(1),
	Run:   runProfile,
}

var relationshipsCmd = &cobra.Command{
	Use:   "relationships",
	Short: "Discover relationships between schemas",
	Run:   runRelationships,
}

var qualityCmd = &cobra.Command{
	Use:   "quality [schema-name]",
	Short: "Assess data quality for a schema",
	Args:  cobra.ExactArgs(1),
	Run:   runQuality,
}

var healthCmd = &cobra.Command{
	Use:   "health",
	Short: "Check discovery engine health",
	Run:   runHealth,
}

func init() {
	// Global flags
	rootCmd.PersistentFlags().StringVarP(&configFile, "config", "c", "", "config file (default is ./discovery.yaml)")
	rootCmd.PersistentFlags().StringVarP(&outputFormat, "output", "o", "json", "output format (json, yaml, table)")
	rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "verbose output")
	
	// Discover command flags
	discoverCmd.Flags().IntVar(&maxSchemas, "max-schemas", 50, "maximum number of schemas to discover")
	discoverCmd.Flags().IntVar(&minRecords, "min-records", 100, "minimum record count for schema inclusion")
	discoverCmd.Flags().StringSliceVar(&eventTypes, "event-types", []string{}, "specific event types to discover")
	discoverCmd.Flags().StringSliceVar(&keywords, "keywords", []string{}, "keywords for intelligent discovery")
	discoverCmd.Flags().StringVar(&purpose, "purpose", "", "discovery purpose (e.g., 'performance analysis')")
	discoverCmd.Flags().StringVar(&domain, "domain", "", "domain focus (e.g., 'apm', 'infrastructure', 'logs')")
	
	// Profile command flags
	profileCmd.Flags().StringVar(&profileDepth, "depth", "standard", "profiling depth (basic, standard, full)")
	
	// Add commands
	rootCmd.AddCommand(discoverCmd)
	rootCmd.AddCommand(profileCmd)
	rootCmd.AddCommand(relationshipsCmd)
	rootCmd.AddCommand(qualityCmd)
	rootCmd.AddCommand(healthCmd)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func runDiscover(cmd *cobra.Command, args []string) {
	engine, err := createEngine()
	if err != nil {
		log.Fatal("Failed to create engine:", err)
	}
	
	ctx := context.Background()
	
	// Check if intelligent discovery is requested
	if len(keywords) > 0 || purpose != "" || domain != "" {
		// Use intelligent discovery
		hints := discovery.DiscoveryHints{
			Keywords: keywords,
			Purpose:  purpose,
			Domain:   domain,
		}
		
		if verbose {
			fmt.Printf("Starting intelligent discovery with hints: %+v\n", hints)
		}
		
		result, err := engine.DiscoverWithIntelligence(ctx, hints)
		if err != nil {
			log.Fatal("Discovery failed:", err)
		}
		
		outputDiscoveryResult(result)
	} else {
		// Use standard discovery
		filter := discovery.DiscoveryFilter{
			MaxSchemas:     maxSchemas,
			MinRecordCount: minRecords,
			EventTypes:     eventTypes,
		}
		
		if verbose {
			fmt.Printf("Starting standard discovery with filter: %+v\n", filter)
		}
		
		schemas, err := engine.DiscoverSchemas(ctx, filter)
		if err != nil {
			log.Fatal("Discovery failed:", err)
		}
		
		outputSchemas(schemas)
	}
}

func runProfile(cmd *cobra.Command, args []string) {
	engine, err := createEngine()
	if err != nil {
		log.Fatal("Failed to create engine:", err)
	}
	
	eventType := args[0]
	depth := parseProfileDepth(profileDepth)
	
	ctx := context.Background()
	
	if verbose {
		fmt.Printf("Profiling schema: %s (depth: %s)\n", eventType, profileDepth)
	}
	
	schema, err := engine.ProfileSchema(ctx, eventType, depth)
	if err != nil {
		log.Fatal("Profile failed:", err)
	}
	
	outputSchema(schema)
}

func runRelationships(cmd *cobra.Command, args []string) {
	engine, err := createEngine()
	if err != nil {
		log.Fatal("Failed to create engine:", err)
	}
	
	ctx := context.Background()
	
	// First discover schemas
	filter := discovery.DiscoveryFilter{
		MaxSchemas:     maxSchemas,
		MinRecordCount: minRecords,
	}
	
	if verbose {
		fmt.Println("Discovering schemas for relationship analysis...")
	}
	
	schemas, err := engine.DiscoverSchemas(ctx, filter)
	if err != nil {
		log.Fatal("Schema discovery failed:", err)
	}
	
	if verbose {
		fmt.Printf("Found %d schemas, analyzing relationships...\n", len(schemas))
	}
	
	relationships, err := engine.FindRelationships(ctx, schemas)
	if err != nil {
		log.Fatal("Relationship discovery failed:", err)
	}
	
	outputRelationships(relationships)
}

func runQuality(cmd *cobra.Command, args []string) {
	engine, err := createEngine()
	if err != nil {
		log.Fatal("Failed to create engine:", err)
	}
	
	schemaName := args[0]
	ctx := context.Background()
	
	if verbose {
		fmt.Printf("Assessing quality for schema: %s\n", schemaName)
	}
	
	report, err := engine.AssessQuality(ctx, schemaName)
	if err != nil {
		log.Fatal("Quality assessment failed:", err)
	}
	
	outputQualityReport(report)
}

func runHealth(cmd *cobra.Command, args []string) {
	engine, err := createEngine()
	if err != nil {
		log.Fatal("Failed to create engine:", err)
	}
	
	health := engine.Health()
	outputHealth(health)
}

func createEngine() (*discovery.Engine, error) {
	var config *discovery.Config
	
	if configFile != "" {
		// Load config from file
		cfg, err := discovery.LoadConfig(configFile)
		if err != nil {
			return nil, fmt.Errorf("loading config: %w", err)
		}
		config = cfg
	} else {
		// Use default config
		config = discovery.DefaultConfig()
	}
	
	return discovery.NewEngine(config)
}

func parseProfileDepth(depth string) discovery.ProfileDepth {
	switch strings.ToLower(depth) {
	case "basic":
		return discovery.ProfileDepthBasic
	case "full":
		return discovery.ProfileDepthFull
	default:
		return discovery.ProfileDepthStandard
	}
}

// Output functions

func outputDiscoveryResult(result *discovery.DiscoveryResult) {
	switch outputFormat {
	case "json":
		data, _ := json.MarshalIndent(result, "", "  ")
		fmt.Println(string(data))
	case "table":
		fmt.Printf("Discovered Schemas: %d\n", len(result.Schemas))
		fmt.Printf("Patterns Found: %d\n", len(result.Patterns))
		fmt.Printf("Insights: %d\n", len(result.Insights))
		fmt.Printf("\nTop Schemas:\n")
		for i, schema := range result.Schemas {
			if i >= 10 {
				break
			}
			fmt.Printf("  %2d. %-30s Records: %8d Quality: %.2f\n",
				i+1, schema.Name, schema.SampleCount, schema.Quality.OverallScore)
		}
		fmt.Printf("\nKey Insights:\n")
		for i, insight := range result.Insights {
			if i >= 5 {
				break
			}
			fmt.Printf("  - [%s] %s\n", insight.Severity, insight.Title)
		}
		fmt.Printf("\nRecommendations:\n")
		for i, rec := range result.Recommendations {
			if i >= 5 {
				break
			}
			fmt.Printf("  - %s\n", rec)
		}
	default:
		log.Fatal("Unsupported output format:", outputFormat)
	}
}

func outputSchemas(schemas []discovery.Schema) {
	switch outputFormat {
	case "json":
		data, _ := json.MarshalIndent(schemas, "", "  ")
		fmt.Println(string(data))
	case "table":
		fmt.Printf("Discovered %d schemas:\n\n", len(schemas))
		fmt.Printf("%-30s %-15s %10s %8s\n", "Schema Name", "Event Type", "Records", "Quality")
		fmt.Println(strings.Repeat("-", 70))
		for _, schema := range schemas {
			fmt.Printf("%-30s %-15s %10d %8.2f\n",
				schema.Name, schema.EventType, schema.SampleCount, schema.Quality.OverallScore)
		}
	default:
		log.Fatal("Unsupported output format:", outputFormat)
	}
}

func outputSchema(schema *discovery.Schema) {
	switch outputFormat {
	case "json":
		data, _ := json.MarshalIndent(schema, "", "  ")
		fmt.Println(string(data))
	case "table":
		fmt.Printf("Schema: %s\n", schema.Name)
		fmt.Printf("Event Type: %s\n", schema.EventType)
		fmt.Printf("Sample Count: %d\n", schema.SampleCount)
		fmt.Printf("Quality Score: %.2f\n", schema.Quality.OverallScore)
		fmt.Printf("Discovered: %s\n", schema.DiscoveredAt.Format(time.RFC3339))
		fmt.Printf("\nAttributes (%d):\n", len(schema.Attributes))
		fmt.Printf("%-25s %-15s %-15s %12s\n", "Name", "Data Type", "Semantic Type", "Cardinality")
		fmt.Println(strings.Repeat("-", 70))
		for _, attr := range schema.Attributes {
			semanticType := string(attr.SemanticType)
			if semanticType == "" {
				semanticType = "-"
			}
			cardinality := "-"
			if attr.Cardinality.IsHighCardinality {
				cardinality = fmt.Sprintf("High (%.0f%%)", attr.Cardinality.Ratio*100)
			}
			fmt.Printf("%-25s %-15s %-15s %12s\n",
				attr.Name, attr.DataType, semanticType, cardinality)
		}
		if len(schema.Patterns) > 0 {
			fmt.Printf("\nDetected Patterns:\n")
			for _, pattern := range schema.Patterns {
				fmt.Printf("  - %s: %s (confidence: %.2f)\n",
					pattern.Type, pattern.Description, pattern.Confidence)
			}
		}
	default:
		log.Fatal("Unsupported output format:", outputFormat)
	}
}

func outputRelationships(relationships []discovery.Relationship) {
	switch outputFormat {
	case "json":
		data, _ := json.MarshalIndent(relationships, "", "  ")
		fmt.Println(string(data))
	case "table":
		fmt.Printf("Found %d relationships:\n\n", len(relationships))
		fmt.Printf("%-20s %-20s %-15s %10s\n", "Source", "Target", "Type", "Confidence")
		fmt.Println(strings.Repeat("-", 70))
		for _, rel := range relationships {
			fmt.Printf("%-20s %-20s %-15s %10.2f\n",
				rel.SourceSchema, rel.TargetSchema, rel.Type, rel.Confidence)
			if rel.JoinKeys != nil {
				fmt.Printf("  Join: %s <-> %s (%s)\n",
					rel.JoinKeys.SourceKey, rel.JoinKeys.TargetKey, rel.JoinKeys.JoinType)
			}
		}
	default:
		log.Fatal("Unsupported output format:", outputFormat)
	}
}

func outputQualityReport(report *discovery.QualityReport) {
	switch outputFormat {
	case "json":
		data, _ := json.MarshalIndent(report, "", "  ")
		fmt.Println(string(data))
	case "table":
		fmt.Printf("Quality Report for: %s\n", report.SchemaName)
		fmt.Printf("Overall Score: %.2f\n", report.OverallScore)
		fmt.Printf("Sample Size: %d\n", report.SampleSize)
		fmt.Printf("\nDimensions:\n")
		fmt.Printf("  Completeness: %.2f\n", report.Dimensions.Completeness.Score)
		fmt.Printf("  Consistency:  %.2f\n", report.Dimensions.Consistency.Score)
		fmt.Printf("  Timeliness:   %.2f\n", report.Dimensions.Timeliness.Score)
		fmt.Printf("  Uniqueness:   %.2f\n", report.Dimensions.Uniqueness.Score)
		fmt.Printf("  Validity:     %.2f\n", report.Dimensions.Validity.Score)
		
		if len(report.Issues) > 0 {
			fmt.Printf("\nIssues:\n")
			for _, issue := range report.Issues {
				fmt.Printf("  [%s] %s - %s\n", issue.Severity, issue.Dimension, issue.Description)
			}
		}
		
		if len(report.Recommendations) > 0 {
			fmt.Printf("\nRecommendations:\n")
			for _, rec := range report.Recommendations {
				fmt.Printf("  - %s\n", rec)
			}
		}
	default:
		log.Fatal("Unsupported output format:", outputFormat)
	}
}

func outputHealth(health discovery.HealthStatus) {
	switch outputFormat {
	case "json":
		data, _ := json.MarshalIndent(health, "", "  ")
		fmt.Println(string(data))
	case "table":
		fmt.Printf("Discovery Engine Health\n")
		fmt.Printf("Status: %s\n", health.Status)
		fmt.Printf("Version: %s\n", health.Version)
		fmt.Printf("Uptime: %s\n", health.Uptime)
		fmt.Printf("\nComponents:\n")
		for name, comp := range health.Components {
			fmt.Printf("  %-15s %s\n", name+":", comp.Status)
			if comp.Message != "" {
				fmt.Printf("    %s\n", comp.Message)
			}
		}
		fmt.Printf("\nMetrics:\n")
		for name, value := range health.Metrics {
			fmt.Printf("  %-25s %v\n", name+":", value)
		}
	default:
		log.Fatal("Unsupported output format:", outputFormat)
	}
}