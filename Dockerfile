# Dockerfile for UDS Core (Go services)
FROM golang:1.21-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git make

# Set working directory
WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build server binary
RUN go build -o bin/mcp-server ./cmd/server

# Final stage
FROM alpine:latest

# Install runtime dependencies
RUN apk add --no-cache ca-certificates

# Create non-root user
RUN adduser -D -u 1000 uds

# Set working directory
WORKDIR /app

# Copy server binary from builder
COPY --from=builder /app/bin/mcp-server /app/bin/

# Copy configuration files
COPY --from=builder /app/config /app/config

# Create directories
RUN mkdir -p /app/logs /app/data && \
    chown -R uds:uds /app

# Switch to non-root user
USER uds

# Expose ports
EXPOSE 3333 8080 8081

# Default command
CMD ["/app/bin/mcp-server"]