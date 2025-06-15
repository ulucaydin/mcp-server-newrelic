package cmd

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"text/tabwriter"
	"time"

	"github.com/spf13/cobra"
	"gopkg.in/yaml.v3"
)

// discoveryCmd represents the discovery command
var discoveryCmd = &cobra.Command{
	Use:   "discovery",
	Short: "Discover and explore data schemas",
	Long:  `Use discovery commands to explore available data schemas, analyze their structure, find relationships, and assess data quality.`,
}

// listCmd lists available schemas
var listCmd = &cobra.Command{
	Use:   "list",
	Short: "List available schemas",
	Long:  `List all discovered data schemas with basic information about record counts and quality scores.`,
	RunE:  runDiscoveryList,
}

// profileCmd shows detailed schema profile
var profileCmd = &cobra.Command{
	Use:   "profile <event-type>",
	Short: "Get detailed schema profile",
	Long:  `Display detailed information about a specific schema including attributes, patterns, and sample data.`,
	Args:  cobra.ExactArgs(1),
	RunE:  runDiscoveryProfile,
}

// relationshipsCmd finds relationships between schemas
var relationshipsCmd = &cobra.Command{
	Use:   "relationships <schema1> <schema2> [schema3...]",
	Short: "Find relationships between schemas",
	Long:  `Discover relationships such as joins, correlations, and hierarchies between multiple schemas.`,
	Args:  cobra.MinimumNArgs(2),
	RunE:  runDiscoveryRelationships,
}

// qualityCmd assesses data quality
var qualityCmd = &cobra.Command{
	Use:   "quality <event-type>",
	Short: "Assess data quality",
	Long:  `Get a comprehensive quality assessment report for a schema including metrics, issues, and recommendations.`,
	Args:  cobra.ExactArgs(1),
	RunE:  runDiscoveryQuality,
}

func init() {
	// Add subcommands
	discoveryCmd.AddCommand(listCmd)
	discoveryCmd.AddCommand(profileCmd)
	discoveryCmd.AddCommand(relationshipsCmd)
	discoveryCmd.AddCommand(qualityCmd)

	// List command flags
	listCmd.Flags().String("filter", "", "Filter by event type pattern")
	listCmd.Flags().Int64("min-records", 0, "Minimum record count")
	listCmd.Flags().Int("max-schemas", 50, "Maximum schemas to return")
	listCmd.Flags().Bool("metadata", false, "Include metadata in response")

	// Profile command flags
	profileCmd.Flags().String("depth", "standard", "Profile depth (basic, standard, full)")

	// Relationships command flags
	relationshipsCmd.Flags().Int("max", 10, "Maximum relationships to return")
	relationshipsCmd.Flags().Float64("min-confidence", 0.7, "Minimum confidence threshold")

	// Quality command flags
	qualityCmd.Flags().String("time-range", "24h", "Time range for quality assessment")
}

func runDiscoveryList(cmd *cobra.Command, args []string) error {
	// Build query parameters
	params := make(map[string]string)
	if filter, _ := cmd.Flags().GetString("filter"); filter != "" {
		params["eventType"] = filter
	}
	if minRecords, _ := cmd.Flags().GetInt64("min-records"); minRecords > 0 {
		params["minRecordCount"] = fmt.Sprintf("%d", minRecords)
	}
	if maxSchemas, _ := cmd.Flags().GetInt("max-schemas"); maxSchemas > 0 {
		params["maxSchemas"] = fmt.Sprintf("%d", maxSchemas)
	}
	if metadata, _ := cmd.Flags().GetBool("metadata"); metadata {
		params["includeMetadata"] = "true"
	}

	// Make API request
	resp, err := makeAPIRequest("GET", "/discovery/schemas", params, nil)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// Parse response
	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return fmt.Errorf("failed to decode response: %w", err)
	}

	// Output results
	return outputResult(result)
}

func runDiscoveryProfile(cmd *cobra.Command, args []string) error {
	eventType := args[0]
	depth, _ := cmd.Flags().GetString("depth")

	params := map[string]string{
		"depth": depth,
	}

	resp, err := makeAPIRequest("GET", fmt.Sprintf("/discovery/schemas/%s", eventType), params, nil)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return fmt.Errorf("failed to decode response: %w", err)
	}

	return outputResult(result)
}

func runDiscoveryRelationships(cmd *cobra.Command, args []string) error {
	maxRels, _ := cmd.Flags().GetInt("max")
	minConf, _ := cmd.Flags().GetFloat64("min-confidence")

	body := map[string]interface{}{
		"schemas": args,
		"options": map[string]interface{}{
			"maxRelationships": maxRels,
			"minConfidence":    minConf,
		},
	}

	resp, err := makeAPIRequest("POST", "/discovery/relationships", nil, body)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return fmt.Errorf("failed to decode response: %w", err)
	}

	return outputResult(result)
}

func runDiscoveryQuality(cmd *cobra.Command, args []string) error {
	eventType := args[0]
	timeRange, _ := cmd.Flags().GetString("time-range")

	params := map[string]string{
		"timeRange": timeRange,
	}

	resp, err := makeAPIRequest("GET", fmt.Sprintf("/discovery/quality/%s", eventType), params, nil)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return fmt.Errorf("failed to decode response: %w", err)
	}

	return outputResult(result)
}

// Helper functions

func makeAPIRequest(method, path string, params map[string]string, body interface{}) (*http.Response, error) {
	client := &http.Client{
		Timeout: 30 * time.Second,
	}

	url := apiURL + path

	// Add query parameters
	if len(params) > 0 {
		query := make([]string, 0, len(params))
		for k, v := range params {
			query = append(query, fmt.Sprintf("%s=%s", k, v))
		}
		url += "?" + strings.Join(query, "&")
	}

	var bodyReader io.Reader
	if body != nil {
		bodyBytes, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal request body: %w", err)
		}
		bodyReader = strings.NewReader(string(bodyBytes))
	}

	req, err := http.NewRequest(method, url, bodyReader)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	if verbose {
		fmt.Fprintf(os.Stderr, "Request: %s %s\n", method, url)
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}

	if resp.StatusCode >= 400 {
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		return nil, fmt.Errorf("API error (status %d): %s", resp.StatusCode, string(body))
	}

	return resp, nil
}

func outputResult(result interface{}) error {
	switch output {
	case "json":
		encoder := json.NewEncoder(os.Stdout)
		encoder.SetIndent("", "  ")
		return encoder.Encode(result)

	case "yaml":
		encoder := yaml.NewEncoder(os.Stdout)
		encoder.SetIndent(2)
		return encoder.Encode(result)

	case "table":
		return outputTable(result)

	default:
		return fmt.Errorf("unsupported output format: %s", output)
	}
}

func outputTable(result interface{}) error {
	// Type assertion to handle different result types
	switch v := result.(type) {
	case map[string]interface{}:
		if schemas, ok := v["schemas"].([]interface{}); ok {
			return outputSchemasTable(schemas)
		}
		if relationships, ok := v["relationships"].([]interface{}); ok {
			return outputRelationshipsTable(relationships)
		}
		// For single objects, output as key-value pairs
		return outputKeyValueTable(v)
	default:
		// Fallback to JSON for complex types
		encoder := json.NewEncoder(os.Stdout)
		encoder.SetIndent("", "  ")
		return encoder.Encode(result)
	}
}

func outputSchemasTable(schemas []interface{}) error {
	w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
	fmt.Fprintln(w, "EVENT TYPE\tRECORDS\tATTRIBUTES\tQUALITY\tLAST ANALYZED")

	for _, s := range schemas {
		schema := s.(map[string]interface{})
		eventType := schema["eventType"].(string)
		records := int64(0)
		if r, ok := schema["recordCount"].(float64); ok {
			records = int64(r)
		}
		attrs := 0
		if a, ok := schema["attributes"].([]interface{}); ok {
			attrs = len(a)
		}
		quality := 0.0
		if q, ok := schema["quality"].(map[string]interface{}); ok {
			if score, ok := q["overallScore"].(float64); ok {
				quality = score
			}
		}
		lastAnalyzed := "N/A"
		if la, ok := schema["lastAnalyzed"].(string); ok {
			lastAnalyzed = la
		}

		fmt.Fprintf(w, "%s\t%d\t%d\t%.2f\t%s\n", eventType, records, attrs, quality, lastAnalyzed)
	}

	return w.Flush()
}

func outputRelationshipsTable(relationships []interface{}) error {
	w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
	fmt.Fprintln(w, "TYPE\tSOURCE\tTARGET\tATTRIBUTE\tCONFIDENCE")

	for _, r := range relationships {
		rel := r.(map[string]interface{})
		relType := rel["type"].(string)
		source := rel["sourceSchema"].(string)
		target := rel["targetSchema"].(string)
		attr := fmt.Sprintf("%s -> %s", rel["sourceAttribute"], rel["targetAttribute"])
		confidence := rel["confidence"].(float64)

		fmt.Fprintf(w, "%s\t%s\t%s\t%s\t%.2f\n", relType, source, target, attr, confidence)
	}

	return w.Flush()
}

func outputKeyValueTable(data map[string]interface{}) error {
	w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
	
	for k, v := range data {
		fmt.Fprintf(w, "%s:\t%v\n", k, v)
	}

	return w.Flush()
}