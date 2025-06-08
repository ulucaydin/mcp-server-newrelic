#!/bin/bash
# Release automation script for MCP Server New Relic

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Check if version argument is provided
if [ $# -eq 0 ]; then
    print_error "Usage: $0 <version>"
    echo "Example: $0 1.1.0"
    exit 1
fi

VERSION=$1

# Validate version format
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    print_error "Invalid version format. Use semantic versioning (e.g., 1.2.3)"
    exit 1
fi

echo "========================================="
echo "Releasing MCP Server New Relic v$VERSION"
echo "========================================="
echo ""

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    print_error "You must be on the main branch to create a release"
    print_info "Current branch: $CURRENT_BRANCH"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    print_error "You have uncommitted changes. Please commit or stash them first."
    git status --short
    exit 1
fi

# Pull latest changes
print_info "Pulling latest changes from remote..."
git pull origin main

# Run tests
print_info "Running tests..."
if ./scripts/run-tests.sh --all; then
    print_status "All tests passed"
else
    print_error "Tests failed. Fix issues before releasing."
    exit 1
fi

# Update version in files
print_info "Updating version in files..."

# Update pyproject.toml
if [ -f "pyproject.toml" ]; then
    sed -i.bak "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml
    rm pyproject.toml.bak
    print_status "Updated pyproject.toml"
fi

# Update main.py if it has a version
if grep -q "VERSION = " main.py 2>/dev/null; then
    sed -i.bak "s/VERSION = \".*\"/VERSION = \"$VERSION\"/" main.py
    rm main.py.bak
    print_status "Updated main.py"
fi

# Update CHANGELOG.md
print_info "Updating CHANGELOG.md..."
DATE=$(date +%Y-%m-%d)
sed -i.bak "s/## \[Unreleased\]/## [Unreleased]\n\n## [$VERSION] - $DATE/" CHANGELOG.md
rm CHANGELOG.md.bak
print_status "Updated CHANGELOG.md"

# Commit version changes
print_info "Committing version changes..."
git add pyproject.toml main.py CHANGELOG.md
git commit -m "chore: release version $VERSION"

# Create git tag
print_info "Creating git tag..."
git tag -a "v$VERSION" -m "Release version $VERSION"
print_status "Created tag v$VERSION"

# Build distribution packages
print_info "Building distribution packages..."
rm -rf dist/
python -m build
print_status "Distribution packages built"

# Verify packages
print_info "Verifying packages..."
if command -v twine &> /dev/null; then
    twine check dist/*
    print_status "Package verification passed"
else
    print_warning "Twine not installed, skipping package verification"
fi

# Build Docker image
print_info "Building Docker image..."
docker build -t mcp-server-newrelic:$VERSION -t mcp-server-newrelic:latest .
print_status "Docker image built"

# Create release notes
print_info "Creating release notes..."
cat > release-notes-$VERSION.md << EOF
# MCP Server New Relic v$VERSION

Released on $DATE

## What's New

[Add release highlights here]

## Installation

### PyPI
\`\`\`bash
pip install mcp-server-newrelic==$VERSION
\`\`\`

### Docker
\`\`\`bash
docker pull mcp-server-newrelic:$VERSION
\`\`\`

### From Source
\`\`\`bash
git clone https://github.com/newrelic/mcp-server-newrelic.git
cd mcp-server-newrelic
git checkout v$VERSION
pip install -r requirements.txt
\`\`\`

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed changes.

## Contributors

Thank you to all contributors who made this release possible!
EOF

print_status "Release notes created: release-notes-$VERSION.md"

# Summary
echo ""
echo "========================================="
print_status "Release preparation complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Review and edit release-notes-$VERSION.md"
echo "2. Push changes: git push origin main"
echo "3. Push tag: git push origin v$VERSION"
echo "4. Create GitHub release with release notes"
echo "5. Publish to PyPI: twine upload dist/*"
echo "6. Push Docker image: docker push mcp-server-newrelic:$VERSION"
echo ""
print_info "Don't forget to announce the release!"