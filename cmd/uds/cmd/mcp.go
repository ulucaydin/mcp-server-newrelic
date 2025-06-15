package cmd

import (
	"bufio"
	"context"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"

	"github.com/spf13/cobra"
)

// mcpCmd represents the mcp command
var mcpCmd = &cobra.Command{
	Use:   "mcp",
	Short: "Interact via Model Context Protocol",
	Long: `Connect to the UDS MCP server for AI agent interactions.
	
This command starts an interactive MCP session or runs the server.`,
}

// connectCmd connects to MCP server
var connectCmd = &cobra.Command{
	Use:   "connect",
	Short: "Connect to MCP server",
	Long:  `Connect to a running MCP server via stdio transport for interactive sessions.`,
	RunE:  runMCPConnect,
}

// serverCmd runs the MCP server
var serverCmd = &cobra.Command{
	Use:   "server",
	Short: "Start MCP server",
	Long:  `Start the MCP server with specified transport and options.`,
	RunE:  runMCPServer,
}

func init() {
	// Add subcommands
	mcpCmd.AddCommand(connectCmd)
	mcpCmd.AddCommand(serverCmd)

	// Connect command flags
	connectCmd.Flags().String("server", "mcp-server", "Path to MCP server executable")
	connectCmd.Flags().String("transport", "stdio", "Transport type (stdio, http)")

	// Server command flags
	serverCmd.Flags().String("transport", "stdio", "Transport type (stdio, http, sse)")
	serverCmd.Flags().String("host", "localhost", "HTTP server host")
	serverCmd.Flags().Int("port", 9090, "HTTP server port")
	serverCmd.Flags().Duration("timeout", 30, "Request timeout")
	serverCmd.Flags().Bool("debug", false, "Enable debug logging")
}

func runMCPConnect(cmd *cobra.Command, args []string) error {
	serverPath, _ := cmd.Flags().GetString("server")
	transport, _ := cmd.Flags().GetString("transport")

	if transport != "stdio" {
		return fmt.Errorf("only stdio transport is supported for connect command")
	}

	// Start MCP server as subprocess
	serverCmd := exec.Command(serverPath, "--transport", "stdio")
	
	// Get pipes
	stdin, err := serverCmd.StdinPipe()
	if err != nil {
		return fmt.Errorf("failed to get stdin pipe: %w", err)
	}
	
	stdout, err := serverCmd.StdoutPipe()
	if err != nil {
		return fmt.Errorf("failed to get stdout pipe: %w", err)
	}
	
	stderr, err := serverCmd.StderrPipe()
	if err != nil {
		return fmt.Errorf("failed to get stderr pipe: %w", err)
	}

	// Start server
	if err := serverCmd.Start(); err != nil {
		return fmt.Errorf("failed to start server: %w", err)
	}
	defer serverCmd.Wait()

	// Forward stderr to our stderr
	go io.Copy(os.Stderr, stderr)

	// Initialize connection
	if err := sendMCPRequest(stdin, stdout, map[string]interface{}{
		"jsonrpc": "2.0",
		"method":  "initialize",
		"id":      1,
	}); err != nil {
		return fmt.Errorf("failed to initialize: %w", err)
	}

	fmt.Println("Connected to MCP server. Type 'help' for available commands.")

	// Interactive loop
	scanner := bufio.NewScanner(os.Stdin)
	fmt.Print("> ")
	
	for scanner.Scan() {
		line := scanner.Text()
		
		switch line {
		case "help":
			printMCPHelp()
		case "exit", "quit":
			return nil
		case "tools":
			if err := listTools(stdin, stdout); err != nil {
				fmt.Printf("Error: %v\n", err)
			}
		default:
			// Try to execute as a tool
			if err := executeToolCommand(stdin, stdout, line); err != nil {
				fmt.Printf("Error: %v\n", err)
			}
		}
		
		fmt.Print("> ")
	}

	return scanner.Err()
}

func runMCPServer(cmd *cobra.Command, args []string) error {
	transport, _ := cmd.Flags().GetString("transport")
	host, _ := cmd.Flags().GetString("host")
	port, _ := cmd.Flags().GetInt("port")
	timeout, _ := cmd.Flags().GetDuration("timeout")
	debug, _ := cmd.Flags().GetBool("debug")

	// Build command
	serverArgs := []string{
		"--transport", transport,
		"--host", host,
		"--port", fmt.Sprintf("%d", port),
		"--timeout", timeout.String(),
	}
	
	if debug {
		serverArgs = append(serverArgs, "--debug")
	}

	// Execute mcp-server
	serverCmd := exec.CommandContext(context.Background(), "mcp-server", serverArgs...)
	serverCmd.Stdout = os.Stdout
	serverCmd.Stderr = os.Stderr
	serverCmd.Stdin = os.Stdin

	return serverCmd.Run()
}

func sendMCPRequest(stdin io.Writer, stdout io.Reader, request interface{}) error {
	// Marshal request
	data, err := json.Marshal(request)
	if err != nil {
		return fmt.Errorf("failed to marshal request: %w", err)
	}

	// Write length header
	length := uint32(len(data))
	if err := binary.Write(stdin, binary.BigEndian, length); err != nil {
		return fmt.Errorf("failed to write length: %w", err)
	}

	// Write message
	if _, err := stdin.Write(data); err != nil {
		return fmt.Errorf("failed to write message: %w", err)
	}

	// Read response
	reader := bufio.NewReader(stdout)
	
	// Read length header
	var respLength uint32
	if err := binary.Read(reader, binary.BigEndian, &respLength); err != nil {
		return fmt.Errorf("failed to read response length: %w", err)
	}

	// Read message
	respData := make([]byte, respLength)
	if _, err := io.ReadFull(reader, respData); err != nil {
		return fmt.Errorf("failed to read response: %w", err)
	}

	// Parse and display response
	var resp map[string]interface{}
	if err := json.Unmarshal(respData, &resp); err != nil {
		return fmt.Errorf("failed to unmarshal response: %w", err)
	}

	// Check for errors
	if errObj, ok := resp["error"]; ok {
		return fmt.Errorf("server error: %v", errObj)
	}

	// Pretty print result
	if result, ok := resp["result"]; ok {
		resultJSON, _ := json.MarshalIndent(result, "", "  ")
		fmt.Println(string(resultJSON))
	}

	return nil
}

func listTools(stdin io.Writer, stdout io.Reader) error {
	return sendMCPRequest(stdin, stdout, map[string]interface{}{
		"jsonrpc": "2.0",
		"method":  "tools/list",
		"id":      2,
	})
}

func executeToolCommand(stdin io.Writer, stdout io.Reader, command string) error {
	// Simple command parsing (in production, use a proper parser)
	// Format: tool-name [args as JSON]
	
	// For now, just echo the command
	fmt.Printf("Would execute: %s\n", command)
	return nil
}

func printMCPHelp() {
	fmt.Println(`
Available commands:
  help              Show this help message
  tools             List available tools
  exit/quit         Exit the session
  
Tool commands:
  <tool-name> <args>   Execute a tool with arguments
  
Examples:
  discovery.list_schemas
  discovery.profile_attribute {"schema": "Transaction", "attribute": "duration"}
`)
}