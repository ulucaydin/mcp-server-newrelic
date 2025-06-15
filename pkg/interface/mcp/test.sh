#!/bin/bash

# Run tests with nodiscovery build tag to isolate from Track 1
echo "Running MCP tests in isolation from Track 1..."
go test -tags="nodiscovery" -v ./...