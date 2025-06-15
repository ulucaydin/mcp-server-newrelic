package mcp

import (
	"bufio"
	"context"
	"encoding/binary"
	"fmt"
	"io"
	"os"
	"sync"
)

// StdioTransport implements MCP over stdin/stdout
type StdioTransport struct {
	reader  *bufio.Reader
	writer  io.Writer
	handler MessageHandler
	done    chan struct{}
	mu      sync.Mutex
}

// NewStdioTransport creates a new stdio transport
func NewStdioTransport() *StdioTransport {
	return &StdioTransport{
		reader: bufio.NewReader(os.Stdin),
		writer: os.Stdout,
		done:   make(chan struct{}),
	}
}

// Start begins listening for messages on stdin
func (t *StdioTransport) Start(ctx context.Context, handler MessageHandler) error {
	t.handler = handler
	
	// Start read loop
	go t.readLoop(ctx)
	
	// Wait for context cancellation
	<-ctx.Done()
	return ctx.Err()
}

// Send writes a message to stdout
func (t *StdioTransport) Send(message []byte) error {
	t.mu.Lock()
	defer t.mu.Unlock()
	
	// MCP stdio format: length header (4 bytes) + message
	length := int32(len(message))
	
	// Write length header
	if err := binary.Write(t.writer, binary.LittleEndian, length); err != nil {
		return fmt.Errorf("write length: %w", err)
	}
	
	// Write message
	if _, err := t.writer.Write(message); err != nil {
		return fmt.Errorf("write message: %w", err)
	}
	
	// Flush if writer supports it
	if flusher, ok := t.writer.(interface{ Flush() error }); ok {
		if err := flusher.Flush(); err != nil {
			return fmt.Errorf("flush: %w", err)
		}
	}
	
	return nil
}

// Close closes the transport
func (t *StdioTransport) Close() error {
	close(t.done)
	
	// Close stdin if it's a closeable type
	if closer, ok := t.reader.(io.Closer); ok {
		return closer.Close()
	}
	
	return nil
}

// readLoop continuously reads messages from stdin
func (t *StdioTransport) readLoop(ctx context.Context) {
	defer close(t.done)
	
	for {
		select {
		case <-ctx.Done():
			return
		case <-t.done:
			return
		default:
			// Read message with timeout using goroutine
			msgChan := make(chan readResult, 1)
			go t.readMessage(msgChan)
			
			select {
			case <-ctx.Done():
				return
			case <-t.done:
				return
			case result := <-msgChan:
				if result.err != nil {
					if result.err == io.EOF {
						// Clean shutdown
						return
					}
					t.handler.OnError(fmt.Errorf("read error: %w", result.err))
					continue
				}
				
				// Handle message
				response, err := t.handler.HandleMessage(ctx, result.message)
				if err != nil {
					t.handler.OnError(fmt.Errorf("handle message: %w", err))
					continue
				}
				
				// Send response if not nil
				if response != nil {
					if err := t.Send(response); err != nil {
						t.handler.OnError(fmt.Errorf("send response: %w", err))
					}
				}
			}
		}
	}
}

type readResult struct {
	message []byte
	err     error
}

// readMessage reads a single message from stdin
func (t *StdioTransport) readMessage(result chan<- readResult) {
	// Read length header
	var length int32
	if err := binary.Read(t.reader, binary.LittleEndian, &length); err != nil {
		result <- readResult{err: err}
		return
	}
	
	// Validate length
	if length < 0 || length > 100*1024*1024 { // Max 100MB
		result <- readResult{err: fmt.Errorf("invalid message length: %d", length)}
		return
	}
	
	// Read message
	message := make([]byte, length)
	if _, err := io.ReadFull(t.reader, message); err != nil {
		result <- readResult{err: err}
		return
	}
	
	result <- readResult{message: message}
}