# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Documentation search capability with local caching of New Relic docs
- Proper plugin unloading with tool/resource cleanup
- Connection pool reference counting for efficient resource management
- Tests for documentation search, plugin unloading, and connection pooling

### Changed
- Comprehensive security layer with NRQL injection prevention
- Secure API key storage with encryption
- Connection pooling for improved performance
- Advanced caching system with TTL and memory limits
- Rate limiting and query complexity analysis
- Health monitoring with Prometheus metrics export
- Audit logging system for compliance
- Enhanced plugin system with dependency resolution
- Multi-transport support (STDIO, HTTP/SSE)
- Pagination utilities for large result sets
- Infrastructure monitoring plugin
- Logs monitoring plugin
- Comprehensive test suite
- CI/CD pipeline with GitHub Actions
- Pre-commit hooks for code quality
- Makefile for common development tasks
- Docker support with multi-stage builds
- Project packaging with pyproject.toml

### Changed
- Refactored NerdGraph client to use async/await consistently
- Improved error handling with standardized error codes
- Enhanced plugin architecture with metadata and configuration
- Updated all features to use new plugin system
- Improved documentation and code organization

### Fixed
- Fixed circular import issues
- Resolved async/await consistency problems
- Fixed security vulnerabilities in NRQL query handling
- Corrected indentation issues in various modules

### Security
- Implemented NRQL query validation to prevent injection attacks
- Added secure storage for API keys using cryptography library
- Implemented rate limiting to prevent abuse
- Added audit logging for security compliance

## [1.0.0] - 2025-01-06

### Added
- Initial release of MCP Server for New Relic
- Core features: APM, Entities, Alerts, Synthetics monitoring
- Basic NRQL query support
- FastMCP-based server implementation
- Environment-based configuration
- Docker support
- Basic documentation

[Unreleased]: https://github.com/newrelic/mcp-server-newrelic/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/newrelic/mcp-server-newrelic/releases/tag/v1.0.0