package main

import (
	"os"

	"github.com/deepaucksharma/mcp-server-newrelic/cmd/uds/cmd"
)

func main() {
	if err := cmd.Execute(); err != nil {
		os.Exit(1)
	}
}