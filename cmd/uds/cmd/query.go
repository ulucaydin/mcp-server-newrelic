package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
)

// queryCmd represents the query command
var queryCmd = &cobra.Command{
	Use:   "query",
	Short: "Generate and optimize NRQL queries",
	Long:  `Use query commands to generate NRQL queries from natural language descriptions and optimize existing queries.`,
}

// generateCmd generates NRQL from natural language
var generateQueryCmd = &cobra.Command{
	Use:   "generate <description>",
	Short: "Generate NRQL from natural language",
	Long: `Generate NRQL query from a natural language description.
	
Examples:
  uds query generate "show me the average duration of transactions in the last hour"
  uds query generate "find errors by application name"`,
	Args: cobra.MinimumNArgs(1),
	RunE: runQueryGenerate,
}

func init() {
	// Add subcommands
	queryCmd.AddCommand(generateQueryCmd)

	// Generate command flags
	generateQueryCmd.Flags().StringSlice("schemas", []string{}, "Schemas to consider for query generation")
	generateQueryCmd.Flags().String("time-range", "", "Default time range for the query")
	generateQueryCmd.Flags().StringSlice("examples", []string{}, "Example queries for context")
}

func runQueryGenerate(cmd *cobra.Command, args []string) error {
	// Join all args as the prompt
	prompt := ""
	for i, arg := range args {
		if i > 0 {
			prompt += " "
		}
		prompt += arg
	}

	schemas, _ := cmd.Flags().GetStringSlice("schemas")
	timeRange, _ := cmd.Flags().GetString("time-range")
	examples, _ := cmd.Flags().GetStringSlice("examples")

	body := map[string]interface{}{
		"prompt": prompt,
		"context": map[string]interface{}{},
	}

	if len(schemas) > 0 {
		body["context"].(map[string]interface{})["schemas"] = schemas
	}
	if timeRange != "" {
		body["context"].(map[string]interface{})["timeRange"] = timeRange
	}
	if len(examples) > 0 {
		body["context"].(map[string]interface{})["examples"] = examples
	}

	resp, err := makeAPIRequest("POST", "/query/generate", nil, body)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// For now, query generation is not implemented
	return fmt.Errorf("query generation not yet implemented in the API")
}