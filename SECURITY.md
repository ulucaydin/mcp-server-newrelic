# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of MCP Server for New Relic seriously. If you have discovered a security vulnerability, please follow these steps:

### 1. Do NOT Create a Public Issue

Security vulnerabilities should not be reported through public GitHub issues.

### 2. Email Us Directly

Please email security reports to: [security@newrelic.com](mailto:security@newrelic.com)

Include the following information:
- Type of vulnerability (e.g., injection, authentication bypass, etc.)
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact assessment and potential attack scenarios

### 3. Response Timeline

- **Initial Response**: Within 48 hours
- **Vulnerability Confirmation**: Within 7 days
- **Fix Development**: Varies based on complexity
- **Security Advisory**: Published after fix is released

## Security Best Practices

When using MCP Server for New Relic:

### API Key Management

1. **Never commit API keys** to version control
2. Store API keys in environment variables or secure vaults
3. Use read-only API keys when possible
4. Rotate API keys regularly
5. Use different keys for different environments

### Deployment Security

1. **Run with minimal privileges**
   - Don't run as root/administrator
   - Use dedicated service accounts

2. **Network Security**
   - Use HTTPS for all API communications
   - Restrict network access to the MCP server
   - Use firewall rules to limit connections

3. **Container Security**
   - Use official base images
   - Scan images for vulnerabilities
   - Don't run containers as root
   - Keep base images updated

### Configuration Security

1. **Validate all inputs**
   - The server validates NRQL queries to prevent injection
   - Don't disable security features

2. **Audit logging**
   - Enable audit logging for compliance
   - Monitor logs for suspicious activity
   - Store logs securely

3. **Access control**
   - Limit who can access the MCP server
   - Use authentication for HTTP transport
   - Implement rate limiting

## Security Features

The MCP Server includes several security features:

### NRQL Injection Prevention
- All NRQL queries are validated before execution
- Dangerous keywords are blocked
- Query complexity limits prevent resource exhaustion

### Secure Key Storage
- API keys can be encrypted at rest
- Keys are never logged or exposed in responses
- Support for external key management systems

### Rate Limiting
- Configurable rate limits per tool
- Prevents abuse and resource exhaustion
- Automatic backoff for repeated failures

### Audit Logging
- All tool invocations are logged
- Includes user, timestamp, and parameters
- Helps with compliance and security monitoring

## Security Checklist

Before deploying to production:

- [ ] API keys are stored securely (not in code)
- [ ] Network access is restricted appropriately
- [ ] Audit logging is enabled
- [ ] Rate limiting is configured
- [ ] Latest security patches are applied
- [ ] Container images are scanned
- [ ] Least privilege principle is followed
- [ ] Input validation is enabled
- [ ] Error messages don't expose sensitive data
- [ ] Dependencies are up to date

## Vulnerability Disclosure

We follow responsible disclosure practices:

1. Security issues are fixed in private
2. Security advisories are published after fixes are available
3. Credit is given to security researchers (with permission)
4. CVEs are assigned for significant vulnerabilities

## Security Updates

Stay informed about security updates:

1. Watch the repository for releases
2. Subscribe to security advisories
3. Check the CHANGELOG for security fixes
4. Follow [@newrelic](https://twitter.com/newrelic) for announcements

## Contact

For security concerns, contact:
- Email: security@newrelic.com
- GPG Key: [Available on request]

For general questions, use GitHub issues.

Thank you for helping keep MCP Server for New Relic secure!