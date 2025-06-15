package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"gopkg.in/yaml.v3"
)

// configCmd represents the config command
var configCmd = &cobra.Command{
	Use:   "config",
	Short: "Manage UDS CLI configuration",
	Long:  `View and manage UDS CLI configuration including API endpoints, authentication, and preferences.`,
}

// showCmd shows current configuration
var showCmd = &cobra.Command{
	Use:   "show",
	Short: "Show current configuration",
	Long:  `Display the current UDS CLI configuration from all sources (file, environment, flags).`,
	RunE:  runConfigShow,
}

// setCmd sets configuration values
var setCmd = &cobra.Command{
	Use:   "set <key> <value>",
	Short: "Set configuration value",
	Long: `Set a configuration value in the config file.
	
Examples:
  uds config set api-url https://uds.newrelic.com/api/v1
  uds config set output json`,
	Args: cobra.ExactArgs(2),
	RunE: runConfigSet,
}

// initConfigCmd initializes configuration
var initConfigCmd = &cobra.Command{
	Use:   "init",
	Short: "Initialize configuration file",
	Long:  `Create a new configuration file with default values.`,
	RunE:  runConfigInit,
}

func init() {
	// Add subcommands
	configCmd.AddCommand(showCmd)
	configCmd.AddCommand(setCmd)
	configCmd.AddCommand(initConfigCmd)
}

func runConfigShow(cmd *cobra.Command, args []string) error {
	fmt.Println("Current UDS CLI Configuration:")
	fmt.Println("==============================")
	
	// Show all settings
	settings := viper.AllSettings()
	
	// Convert to YAML for nice display
	yamlData, err := yaml.Marshal(settings)
	if err != nil {
		return fmt.Errorf("failed to format configuration: %w", err)
	}
	
	fmt.Println(string(yamlData))
	
	// Show config file location
	if configFile := viper.ConfigFileUsed(); configFile != "" {
		fmt.Printf("\nConfig file: %s\n", configFile)
	} else {
		fmt.Println("\nNo config file found. Using defaults and environment variables.")
	}
	
	return nil
}

func runConfigSet(cmd *cobra.Command, args []string) error {
	key := args[0]
	value := args[1]
	
	// Set the value
	viper.Set(key, value)
	
	// Get config file path
	configFile := viper.ConfigFileUsed()
	if configFile == "" {
		// Create default config file
		home, err := os.UserHomeDir()
		if err != nil {
			return fmt.Errorf("failed to get home directory: %w", err)
		}
		
		configDir := filepath.Join(home, ".config")
		if err := os.MkdirAll(configDir, 0755); err != nil {
			return fmt.Errorf("failed to create config directory: %w", err)
		}
		
		configFile = filepath.Join(configDir, ".uds.yaml")
	}
	
	// Write configuration
	if err := viper.WriteConfigAs(configFile); err != nil {
		return fmt.Errorf("failed to write config: %w", err)
	}
	
	fmt.Printf("Set %s = %s\n", key, value)
	fmt.Printf("Configuration saved to: %s\n", configFile)
	
	return nil
}

func runConfigInit(cmd *cobra.Command, args []string) error {
	home, err := os.UserHomeDir()
	if err != nil {
		return fmt.Errorf("failed to get home directory: %w", err)
	}
	
	configDir := filepath.Join(home, ".config")
	if err := os.MkdirAll(configDir, 0755); err != nil {
		return fmt.Errorf("failed to create config directory: %w", err)
	}
	
	configFile := filepath.Join(configDir, ".uds.yaml")
	
	// Check if file already exists
	if _, err := os.Stat(configFile); err == nil {
		return fmt.Errorf("config file already exists: %s", configFile)
	}
	
	// Create default configuration
	defaultConfig := map[string]interface{}{
		"api-url": "http://localhost:8080/api/v1",
		"output":  "table",
		"verbose": false,
		"discovery": map[string]interface{}{
			"default-depth":     "standard",
			"max-schemas":       50,
			"min-confidence":    0.7,
		},
		"mcp": map[string]interface{}{
			"server-path": "mcp-server",
			"transport":   "stdio",
		},
	}
	
	// Write configuration
	configData, err := yaml.Marshal(defaultConfig)
	if err != nil {
		return fmt.Errorf("failed to marshal config: %w", err)
	}
	
	if err := os.WriteFile(configFile, configData, 0644); err != nil {
		return fmt.Errorf("failed to write config file: %w", err)
	}
	
	fmt.Printf("Configuration file created: %s\n", configFile)
	fmt.Println("\nDefault configuration:")
	fmt.Println(string(configData))
	
	return nil
}