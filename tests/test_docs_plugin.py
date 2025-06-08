"""
Tests for the documentation search plugin
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import tempfile

from features.docs import DocsPlugin
from core.docs_cache import DocsCache


class TestDocsCache:
    """Test documentation cache functionality"""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def mock_repo(self):
        """Mock git repository"""
        repo = MagicMock()
        repo.remotes.origin.fetch = MagicMock()
        repo.remotes.origin.pull = MagicMock()
        repo.head.commit.committed_datetime.isoformat.return_value = "2025-01-01T00:00:00"
        repo.head.commit.__str__.return_value = "abc123def456"
        repo.active_branch.name = "main"
        return repo
    
    def test_docs_cache_init(self, temp_cache_dir):
        """Test docs cache initialization"""
        cache = DocsCache(cache_dir=temp_cache_dir)
        assert cache.cache_dir == temp_cache_dir
        assert cache.repo_url == "https://github.com/newrelic/docs-website.git"
    
    @patch('core.docs_cache.git.Repo')
    def test_search(self, mock_git_repo, temp_cache_dir, mock_repo):
        """Test documentation search"""
        mock_git_repo.return_value = mock_repo
        
        # Create test docs
        docs_dir = temp_cache_dir / "src/content/docs"
        docs_dir.mkdir(parents=True)
        
        # Create test document
        test_doc = docs_dir / "test.md"
        test_doc.write_text("""---
title: Test Document
---

# Test Document

This document contains information about NRQL queries and how to use them effectively.
""")
        
        cache = DocsCache(cache_dir=temp_cache_dir)
        cache.repo = mock_repo
        
        # Search for NRQL
        results = cache.search("NRQL", limit=5)
        
        assert len(results) > 0
        assert any("NRQL" in r.get("excerpt", "") for r in results)
    
    def test_get_content(self, temp_cache_dir):
        """Test retrieving document content"""
        cache = DocsCache(cache_dir=temp_cache_dir)
        
        # Create test document
        test_path = "test/document.md"
        doc_path = temp_cache_dir / test_path
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        doc_path.write_text("# Test Content\n\nThis is test content.")
        
        content = cache.get_content(test_path)
        assert "Test Content" in content
        assert "This is test content." in content
    
    def test_get_content_security(self, temp_cache_dir):
        """Test path traversal prevention"""
        cache = DocsCache(cache_dir=temp_cache_dir)
        
        # Try to access file outside cache dir
        content = cache.get_content("../../etc/passwd")
        assert content == ""
    
    def test_extract_title(self, temp_cache_dir):
        """Test title extraction from markdown"""
        cache = DocsCache(cache_dir=temp_cache_dir)
        
        # Test frontmatter title
        content1 = """---
title: "My Document"
---

# Different Title
"""
        title1 = cache._extract_title(content1)
        assert title1 == "My Document"
        
        # Test heading title
        content2 = "# Heading Title\n\nContent here"
        title2 = cache._extract_title(content2)
        assert title2 == "Heading Title"
        
        # Test no title
        content3 = "Just some content"
        title3 = cache._extract_title(content3)
        assert title3 is None


@pytest.mark.asyncio
class TestDocsPlugin:
    """Test documentation plugin functionality"""
    
    @pytest.fixture
    def mock_app(self):
        """Create mock FastMCP app"""
        app = MagicMock()
        app._tools = {}
        app._resources = {}
        
        # Mock decorators
        def tool_decorator():
            def decorator(func):
                app._tools[func.__name__] = func
                return func
            return decorator
        
        def resource_decorator(uri):
            def decorator(func):
                app._resources[uri] = func
                return func
            return decorator
        
        app.tool = tool_decorator
        app.resource = resource_decorator
        
        return app
    
    @pytest.fixture
    def services(self):
        """Create mock services"""
        return {
            "config": {},
            "nerdgraph": MagicMock(),
            "account_id": "12345"
        }
    
    @patch('features.docs.DocsCache')
    async def test_plugin_registration(self, mock_docs_cache_class, mock_app, services):
        """Test plugin registration"""
        mock_cache = MagicMock()
        mock_docs_cache_class.return_value = mock_cache
        
        # Register plugin
        DocsPlugin.register(mock_app, services)
        
        # Check tools were registered
        assert "search_docs" in mock_app._tools
        assert "update_docs_cache" in mock_app._tools
        assert "get_docs_cache_info" in mock_app._tools
        
        # Check resources were registered
        assert any("docs" in uri for uri in mock_app._resources.keys())
    
    @patch('features.docs.DocsCache')
    async def test_search_docs_tool(self, mock_docs_cache_class, mock_app, services):
        """Test search_docs tool"""
        mock_cache = MagicMock()
        mock_cache.search.return_value = [
            {
                "path": "docs/test.md",
                "title": "Test Doc",
                "excerpt": "...about NRQL queries...",
                "url": "https://docs.newrelic.com/docs/test"
            }
        ]
        mock_docs_cache_class.return_value = mock_cache
        
        # Register plugin
        DocsPlugin.register(mock_app, services)
        
        # Get search_docs tool
        search_docs = mock_app._tools["search_docs"]
        
        # Test search
        result = await search_docs(keyword="NRQL", limit=5)
        result_data = json.loads(result)
        
        assert result_data["keyword"] == "NRQL"
        assert result_data["count"] == 1
        assert len(result_data["results"]) == 1
        assert result_data["results"][0]["title"] == "Test Doc"
    
    @patch('features.docs.DocsCache')
    async def test_get_doc_content_resource(self, mock_docs_cache_class, mock_app, services):
        """Test get_doc_content resource"""
        mock_cache = MagicMock()
        mock_cache.get_content.return_value = "# Document Content\n\nThis is the content."
        mock_docs_cache_class.return_value = mock_cache
        
        # Register plugin
        DocsPlugin.register(mock_app, services)
        
        # Find the resource handler
        doc_resource = None
        for uri, handler in mock_app._resources.items():
            if "docs" in uri:
                doc_resource = handler
                break
        
        assert doc_resource is not None
        
        # Test retrieving content
        result = await doc_resource(path="test/doc.md")
        result_data = json.loads(result)
        
        assert result_data["path"] == "test/doc.md"
        assert "Document Content" in result_data["content"]
        assert result_data["length"] > 0
    
    @patch('features.docs.DocsCache')
    async def test_update_cache_tool(self, mock_docs_cache_class, mock_app, services):
        """Test update_docs_cache tool"""
        mock_cache = MagicMock()
        mock_cache.update_cache = MagicMock()
        mock_cache.get_cache_info.return_value = {
            "initialized": True,
            "path": "/cache/path",
            "size_mb": 100.5
        }
        mock_docs_cache_class.return_value = mock_cache
        
        # Register plugin
        DocsPlugin.register(mock_app, services)
        
        # Get tool
        update_cache = mock_app._tools["update_docs_cache"]
        
        # Test update
        result = await update_cache()
        result_data = json.loads(result)
        
        assert result_data["status"] == "success"
        assert "cache_info" in result_data
        mock_cache.update_cache.assert_called_once()