# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in airflow-unfactor, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email security@prefect.io with details about the vulnerability
3. Include steps to reproduce if possible
4. We will respond within 48 hours to acknowledge receipt

## Security Considerations

### Code Parsing

airflow-unfactor parses Python source code using Python's `ast` module. This is a safe operation that does not execute the code being parsed. However:

- **We never execute user-provided DAG code** — only parse it
- Generated Prefect flow code should be reviewed before execution
- The tool does not make network connections to user-specified endpoints

### Generated Code

The tool generates Python code that users will execute. Please:

- Review generated code before running in production
- Pay special attention to subprocess calls (from BashOperator conversions)
- Verify credential handling matches your security requirements

### External MCP Connections

When `include_external_context=true`, the tool may connect to:

- Prefect documentation servers
- Astronomer migration guidance APIs

These connections:
- Are opt-in (can be disabled with `include_external_context=false`)
- Only send query strings, not your DAG code
- Use HTTPS for transport security

### Dependencies

We regularly update dependencies to address known vulnerabilities. Key dependencies:

- `fastmcp` - MCP protocol handling
- `prefect` - Flow execution (if testing generated code)
- `pydantic` - Input validation

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Best Practices

When using airflow-unfactor:

1. **Review generated code** before committing or executing
2. **Don't convert DAGs containing secrets** — extract credentials first
3. **Use environment variables or Prefect Blocks** for sensitive configuration
4. **Test conversions** in a non-production environment first
5. **Keep dependencies updated** via `uv pip install -U airflow-unfactor`
