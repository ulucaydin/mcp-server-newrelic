"""
Documentation cache for New Relic docs repository
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
import git
import os
import shutil

logger = logging.getLogger(__name__)


class DocsCache:
    """Local cache of the New Relic documentation repository."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize docs cache
        
        Args:
            cache_dir: Directory to store docs cache (defaults to ~/.newrelic-mcp/docs)
        """
        self.cache_dir = cache_dir or Path.home() / ".newrelic-mcp" / "docs"
        self.repo_url = os.getenv(
            "NEWRELIC_DOCS_REPO_URL",
            "https://github.com/newrelic/docs-website.git"
        )
        self.repo: Optional[git.Repo] = None
        self._ensure_cache()

    def _ensure_cache(self):
        """Ensure the docs repository is cloned and up to date"""
        try:
            if not self.cache_dir.exists():
                logger.info(f"Cloning docs repository to {self.cache_dir}")
                self.cache_dir.parent.mkdir(parents=True, exist_ok=True)
                self.repo = git.Repo.clone_from(
                    self.repo_url,
                    self.cache_dir,
                    depth=1,  # Shallow clone for speed
                    single_branch=True,
                    branch="main"
                )
                logger.info("Documentation repository cloned successfully")
            else:
                try:
                    self.repo = git.Repo(self.cache_dir)
                    # Only fetch if enabled via environment
                    if os.getenv("NEWRELIC_DOCS_AUTO_UPDATE", "false").lower() == "true":
                        logger.info("Updating documentation repository...")
                        self.repo.remotes.origin.fetch(depth=1)
                        self.repo.remotes.origin.pull()
                except git.InvalidGitRepositoryError:
                    logger.warning(
                        f"Invalid docs repo at {self.cache_dir}, re-cloning..."
                    )
                    shutil.rmtree(self.cache_dir)
                    self.repo = git.Repo.clone_from(
                        self.repo_url,
                        self.cache_dir,
                        depth=1,
                        single_branch=True,
                        branch="main"
                    )
        except Exception as e:
            logger.error(f"Failed to prepare docs cache: {e}")
            self.repo = None

    def search(self, keyword: str, limit: int = 5, 
               file_types: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """Search Markdown docs for a keyword.
        
        Args:
            keyword: Search term
            limit: Maximum results to return
            file_types: File extensions to search (default: ['.md', '.mdx'])
            
        Returns:
            List of search results with path and excerpt
        """
        if not self.repo:
            logger.warning("Documentation repository not available")
            return []
            
        results: List[Dict[str, str]] = []
        keyword_lower = keyword.lower()
        file_types = file_types or ['.md', '.mdx']
        
        # Search patterns for different doc locations
        search_patterns = [
            "src/content/docs/**/*",
            "src/content/whats-new/**/*",
            "src/i18n/content/**/*"
        ]
        
        files_searched = 0
        for pattern in search_patterns:
            for file_path in self.cache_dir.glob(pattern):
                if len(results) >= limit:
                    break
                    
                if not any(file_path.suffix == ext for ext in file_types):
                    continue
                    
                files_searched += 1
                if files_searched > 1000:  # Prevent excessive searching
                    logger.warning("Search limit reached")
                    break
                
                try:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                    index = text.lower().find(keyword_lower)
                    if index != -1:
                        # Extract context around the match
                        start = max(0, index - 100)
                        end = min(len(text), index + 100)
                        excerpt = text[start:end].strip()
                        
                        # Clean up excerpt
                        if start > 0:
                            excerpt = "..." + excerpt
                        if end < len(text):
                            excerpt = excerpt + "..."
                            
                        # Extract title from frontmatter if available
                        title = self._extract_title(text) or file_path.stem
                        
                        results.append({
                            "path": str(file_path.relative_to(self.cache_dir)),
                            "title": title,
                            "excerpt": excerpt,
                            "url": self._get_doc_url(file_path)
                        })
                except Exception as e:
                    logger.debug(f"Failed reading {file_path}: {e}")
                    
        logger.info(f"Found {len(results)} results for '{keyword}'")
        return results

    def get_content(self, rel_path: str) -> str:
        """Return raw Markdown content for a documentation file.
        
        Args:
            rel_path: Relative path to the doc file
            
        Returns:
            File content or empty string if not found
        """
        if not self.repo:
            logger.warning("Documentation repository not available")
            return ""
            
        doc_path = self.cache_dir / rel_path
        
        # Security check - ensure path is within cache dir
        try:
            doc_path.resolve().relative_to(self.cache_dir.resolve())
        except ValueError:
            logger.error(f"Invalid path: {rel_path}")
            return ""
            
        if not doc_path.exists():
            logger.warning(f"Document not found: {rel_path}")
            return ""
            
        try:
            content = doc_path.read_text(encoding="utf-8", errors="ignore")
            return content
        except Exception as e:
            logger.error(f"Failed to read {doc_path}: {e}")
            return ""

    def _extract_title(self, content: str) -> Optional[str]:
        """Extract title from markdown frontmatter"""
        lines = content.split('\n')
        in_frontmatter = False
        
        for line in lines:
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    break
                    
            if in_frontmatter and line.startswith('title:'):
                title = line[6:].strip()
                # Remove quotes if present
                if title.startswith('"') and title.endswith('"'):
                    title = title[1:-1]
                elif title.startswith("'") and title.endswith("'"):
                    title = title[1:-1]
                return title
                
        # Fallback to first heading
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
                
        return None

    def _get_doc_url(self, file_path: Path) -> str:
        """Generate the web URL for a doc file"""
        rel_path = file_path.relative_to(self.cache_dir)
        
        # Map file paths to docs.newrelic.com URLs
        if str(rel_path).startswith("src/content/docs/"):
            url_path = str(rel_path)[17:]  # Remove src/content/docs/
            url_path = url_path.replace('.mdx', '').replace('.md', '')
            return f"https://docs.newrelic.com/docs/{url_path}"
        elif str(rel_path).startswith("src/content/whats-new/"):
            url_path = str(rel_path)[22:]  # Remove src/content/whats-new/
            url_path = url_path.replace('.mdx', '').replace('.md', '')
            return f"https://docs.newrelic.com/whats-new/{url_path}"
        else:
            # Fallback to GitHub URL
            return f"https://github.com/newrelic/docs-website/blob/main/{rel_path}"

    def update_cache(self):
        """Manually update the documentation cache"""
        if not self.repo:
            logger.error("Repository not initialized")
            return
            
        try:
            logger.info("Updating documentation cache...")
            self.repo.remotes.origin.fetch(depth=1)
            self.repo.remotes.origin.pull()
            logger.info("Documentation cache updated successfully")
        except Exception as e:
            logger.error(f"Failed to update cache: {e}")

    def get_cache_info(self) -> Dict[str, any]:
        """Get information about the cache"""
        if not self.repo or not self.cache_dir.exists():
            return {
                "initialized": False,
                "path": str(self.cache_dir),
                "size": 0,
                "last_update": None
            }
            
        try:
            # Get cache size
            total_size = sum(
                f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file()
            )
            
            # Get last commit info
            last_commit = self.repo.head.commit
            
            return {
                "initialized": True,
                "path": str(self.cache_dir),
                "size": total_size,
                "size_mb": round(total_size / (1024 * 1024), 2),
                "last_update": last_commit.committed_datetime.isoformat(),
                "last_commit": str(last_commit)[:8],
                "branch": self.repo.active_branch.name
            }
        except Exception as e:
            logger.error(f"Failed to get cache info: {e}")
            return {
                "initialized": True,
                "path": str(self.cache_dir),
                "error": str(e)
            }