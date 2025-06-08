# Contributing to MCP Server for New Relic

First off, thank you for considering contributing to MCP Server for New Relic! It's people like you that make this tool better for everyone.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible using our issue template.

**Great Bug Reports** tend to have:
- A quick summary and/or background
- Steps to reproduce (be specific!)
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:
- A clear and descriptive title
- A detailed description of the proposed enhancement
- Explain why this enhancement would be useful
- List any alternatives you've considered

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows the style guidelines
6. Issue that pull request!

## Development Setup

1. Clone your fork:
```bash
git clone https://github.com/your-username/mcp-server-newrelic.git
cd mcp-server-newrelic
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
make install-dev
```

4. Set up pre-commit hooks:
```bash
pre-commit install
```

5. Create a `.env` file with your New Relic credentials:
```bash
cp .env.example .env
# Edit .env with your API key and account ID
```

## Development Workflow

1. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes and test:
```bash
make test
make lint
```

3. Format your code:
```bash
make format
```

4. Commit your changes:
```bash
git add .
git commit -m "feat: add amazing feature"
```

We follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.

5. Push to your fork and submit a pull request

## Style Guidelines

### Python Style

We use:
- Black for code formatting (88 character line length)
- isort for import sorting
- Ruff for linting
- mypy for type checking

Run all checks with:
```bash
make lint
```

### Code Style Guidelines

- Use descriptive variable names
- Add type hints to all function signatures
- Write docstrings for all public functions and classes
- Keep functions small and focused
- Prefer composition over inheritance
- Handle errors explicitly

### Testing Guidelines

- Write tests for all new functionality
- Maintain or improve code coverage
- Use pytest fixtures for reusable test components
- Mock external dependencies (especially New Relic API calls)
- Mark integration tests with `@pytest.mark.integration`

Example test:
```python
@pytest.mark.asyncio
async def test_list_hosts(mock_nerdgraph_client):
    """Test listing infrastructure hosts"""
    # Arrange
    mock_nerdgraph_client.query.return_value = {
        "actor": {
            "entitySearch": {
                "results": {
                    "entities": [{"name": "host1"}, {"name": "host2"}]
                }
            }
        }
    }
    
    # Act
    result = await list_hosts(target_account_id=12345)
    
    # Assert
    assert len(result["entities"]) == 2
    assert result["entities"][0]["name"] == "host1"
```

## Project Structure

```
mcp-server-newrelic/
├── core/              # Core functionality
├── features/          # Feature plugins
├── transports/        # Transport implementations
├── tests/            # Test suite
├── configs/          # Configuration files
└── docs/             # Documentation
```

### Adding a New Plugin

1. Create a new file in `features/`:
```python
# features/my_feature.py
from core.plugin_loader import PluginBase
from fastmcp import FastMCP

class MyFeaturePlugin(PluginBase):
    """Description of your plugin"""
    
    metadata = {
        "name": "MyFeaturePlugin",
        "version": "1.0.0",
        "description": "What this plugin does",
        "author": "Your Name",
        "dependencies": [],  # List other plugins this depends on
        "required_services": ["nerdgraph"],  # Required services
    }
    
    @staticmethod
    def register(app: FastMCP, services: Dict[str, Any]):
        """Register plugin tools"""
        
        @app.tool()
        async def my_tool(param: str) -> Dict[str, Any]:
            """Tool description"""
            # Implementation
            pass
```

2. Add tests in `tests/test_my_feature.py`

3. Update documentation

## Documentation

- Update README.md for user-facing changes
- Add docstrings to all new functions and classes
- Update CHANGELOG.md following Keep a Changelog format
- Create examples for complex features

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create a pull request titled "Release v.X.Y.Z"
4. After merge, tag the release:
```bash
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin v1.2.3
```

## Getting Help

- Check the [documentation](README.md)
- Look through [existing issues](https://github.com/newrelic/mcp-server-newrelic/issues)
- Join our community discussions
- Ask questions in issues with the "question" label

## Recognition

Contributors will be recognized in:
- The CONTRIBUTORS file
- Release notes
- Project documentation

Thank you for contributing!