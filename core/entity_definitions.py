from pathlib import Path
import yaml
from typing import Dict, List, Optional, Any
import git
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EntityDefinitionsCache:
    """Manages local cache of New Relic entity definitions"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the entity definitions cache
        
        Args:
            cache_dir: Directory to store the entity definitions
        """
        self.cache_dir = cache_dir or Path.home() / ".newrelic-mcp" / "entity-definitions"
        self.repo_url = "https://github.com/newrelic/entity-definitions.git"
        self.repo: Optional[git.Repo] = None
        self._ensure_cache()
    
    def _ensure_cache(self):
        """Clone or update entity definitions repo"""
        try:
            if not self.cache_dir.exists():
                logger.info(f"Cloning entity definitions to {self.cache_dir}")
                self.cache_dir.parent.mkdir(parents=True, exist_ok=True)
                self.repo = git.Repo.clone_from(
                    self.repo_url, 
                    self.cache_dir, 
                    depth=1,
                    single_branch=True
                )
                logger.info("Entity definitions cloned successfully")
            else:
                # Check if it's a valid git repo
                try:
                    self.repo = git.Repo(self.cache_dir)
                    # Update if older than 24 hours
                    if self._should_update(self.repo):
                        logger.info("Updating entity definitions...")
                        self.repo.remotes.origin.pull()
                        logger.info("Entity definitions updated")
                except git.InvalidGitRepositoryError:
                    logger.warning(f"Invalid git repository at {self.cache_dir}, re-cloning...")
                    import shutil
                    shutil.rmtree(self.cache_dir)
                    self._ensure_cache()
        except Exception as e:
            logger.error(f"Failed to manage entity definitions cache: {e}")
            # Continue without cache rather than failing
    
    def _should_update(self, repo: git.Repo) -> bool:
        """Check if the repo should be updated
        
        Args:
            repo: Git repository
            
        Returns:
            True if update is needed
        """
        try:
            # Get the last commit date
            last_commit = repo.head.commit
            last_update = datetime.fromtimestamp(last_commit.committed_date)
            
            # Update if older than 24 hours
            return datetime.now() - last_update > timedelta(hours=24)
        except Exception as e:
            logger.warning(f"Could not determine last update time: {e}")
            return True
    
    def get_entity_types(self) -> List[str]:
        """List all available entity types
        
        Returns:
            List of entity type names
        """
        entity_types_dir = self.cache_dir / "entity-types"
        if not entity_types_dir.exists():
            logger.warning("Entity types directory not found")
            return []
        
        return [d.name for d in entity_types_dir.iterdir() if d.is_dir()]
    
    def get_golden_metrics(self, entity_type: str) -> List[Dict[str, Any]]:
        """Get golden metrics for an entity type
        
        Args:
            entity_type: Entity type name
            
        Returns:
            List of golden metric definitions
        """
        metrics_file = self.cache_dir / "entity-types" / entity_type / "golden_metrics.yml"
        if not metrics_file.exists():
            logger.debug(f"No golden metrics found for {entity_type}")
            return []
        
        try:
            with open(metrics_file) as f:
                data = yaml.safe_load(f) or {}
                return data.get("metrics", [])
        except Exception as e:
            logger.error(f"Failed to load golden metrics for {entity_type}: {e}")
            return []
    
    def get_entity_definition(self, entity_type: str) -> Dict[str, Any]:
        """Get complete entity definition
        
        Args:
            entity_type: Entity type name
            
        Returns:
            Entity definition dictionary
        """
        def_file = self.cache_dir / "entity-types" / entity_type / "definition.yml"
        if not def_file.exists():
            raise ValueError(f"Unknown entity type: {entity_type}")
        
        try:
            with open(def_file) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load entity definition for {entity_type}: {e}")
            raise
    
    def get_dashboard_templates(self, entity_type: str) -> List[Dict[str, Any]]:
        """Get dashboard templates for an entity type
        
        Args:
            entity_type: Entity type name
            
        Returns:
            List of dashboard template definitions
        """
        dashboard_dir = self.cache_dir / "entity-types" / entity_type / "dashboard"
        if not dashboard_dir.exists():
            return []
        
        templates = []
        for template_file in dashboard_dir.glob("*.json"):
            try:
                with open(template_file) as f:
                    import json
                    templates.append(json.load(f))
            except Exception as e:
                logger.error(f"Failed to load dashboard template {template_file}: {e}")
        
        return templates
    
    def get_relationships(self, entity_type: str) -> List[Dict[str, Any]]:
        """Get relationship definitions for an entity type
        
        Args:
            entity_type: Entity type name
            
        Returns:
            List of relationship definitions
        """
        # Parse relationships from docs/relationships/*.md
        relationships = []
        rel_docs = self.cache_dir / "docs" / "relationships"
        
        if not rel_docs.exists():
            return relationships
        
        for doc in rel_docs.glob("*.md"):
            try:
                # Simple parser for relationship docs
                content = doc.read_text()
                if entity_type in content:
                    # Extract relationship info
                    relationships.append({
                        "type": doc.stem,
                        "file": str(doc),
                        "involves_entity_type": entity_type
                    })
            except Exception as e:
                logger.error(f"Failed to parse relationship doc {doc}: {e}")
        
        return relationships
    
    def search_definitions(self, query: str) -> List[Dict[str, Any]]:
        """Search entity definitions
        
        Args:
            query: Search query
            
        Returns:
            List of matching definitions with metadata
        """
        results = []
        query_lower = query.lower()
        
        for entity_type in self.get_entity_types():
            try:
                definition = self.get_entity_definition(entity_type)
                
                # Search in various fields
                if (query_lower in entity_type.lower() or
                    query_lower in definition.get("domain", "").lower() or
                    query_lower in definition.get("type", "").lower() or
                    any(query_lower in str(v).lower() for v in definition.values())):
                    
                    results.append({
                        "entity_type": entity_type,
                        "domain": definition.get("domain"),
                        "type": definition.get("type"),
                        "definition": definition
                    })
            except Exception as e:
                logger.debug(f"Error searching {entity_type}: {e}")
        
        return results