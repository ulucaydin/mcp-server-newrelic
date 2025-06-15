package mcp

import (
	"bufio"
	"bytes"
	"context"
	"testing"
	"time"
)

// mockMessageHandler implements MessageHandler for testing
type mockMessageHandler struct {
	messages [][]byte
	errors   []error
}

func (m *mockMessageHandler) HandleMessage(ctx context.Context, message []byte) ([]byte, error) {
	m.messages = append(m.messages, message)
	return []byte(`{"jsonrpc":"2.0","id":1,"result":"ok"}`), nil
}

func (m *mockMessageHandler) OnError(err error) {
	m.errors = append(m.errors, err)
}

func TestStdioTransport(t *testing.T) {
	// Create pipes for testing
	input := bytes.NewBuffer(nil)
	output := bytes.NewBuffer(nil)
	
	transport := &StdioTransport{
		reader: bufio.NewReader(input),
		writer: output,
		done:   make(chan struct{}),
	}
	
	// Test sending a message
	testMsg := []byte(`{"test":"message"}`)
	if err := transport.Send(testMsg); err != nil {
		t.Fatalf("Failed to send message: %v", err)
	}
	
	// Verify message was written with length header
	written := output.Bytes()
	if len(written) < 4 {
		t.Fatal("Message not written with length header")
	}
	
	// Test close
	if err := transport.Close(); err != nil {
		t.Fatalf("Failed to close transport: %v", err)
	}
}

func TestHTTPTransport(t *testing.T) {
	transport := NewHTTPTransport("localhost:0")
	handler := &mockMessageHandler{}
	
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	
	// Start transport in background
	errChan := make(chan error, 1)
	go func() {
		errChan <- transport.Start(ctx, handler)
	}()
	
	// Give server time to start
	time.Sleep(100 * time.Millisecond)
	
	// Stop transport
	if err := transport.Close(); err != nil {
		t.Fatalf("Failed to close transport: %v", err)
	}
	
	cancel()
	
	// Check for errors
	select {
	case err := <-errChan:
		if err != nil && err != context.Canceled {
			t.Fatalf("Transport error: %v", err)
		}
	case <-time.After(1 * time.Second):
		t.Fatal("Transport did not stop")
	}
}

func TestSSETransport(t *testing.T) {
	transport := NewSSETransport("localhost:0")
	handler := &mockMessageHandler{}
	
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	
	// Start transport in background
	errChan := make(chan error, 1)
	go func() {
		errChan <- transport.Start(ctx, handler)
	}()
	
	// Give server time to start
	time.Sleep(100 * time.Millisecond)
	
	// Stop transport
	if err := transport.Close(); err != nil {
		t.Fatalf("Failed to close transport: %v", err)
	}
	
	cancel()
	
	// Check for errors
	select {
	case err := <-errChan:
		if err != nil && err != context.Canceled {
			t.Fatalf("Transport error: %v", err)
		}
	case <-time.After(1 * time.Second):
		t.Fatal("Transport did not stop")
	}
}