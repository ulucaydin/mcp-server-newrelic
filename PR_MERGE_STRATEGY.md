# PR Merge Strategy for MCP Server New Relic

## Current State Analysis

### PR #2: Improve cleanup and plugin unloading
**Status**: OPEN  
**Key Changes**:
1. Connection pool reference counting in NerdGraphClient
2. Proper plugin unloading (removing tools, resources, services)
3. Pin dependency versions
4. Simplify EntitiesPlugin implementation
5. Add backwards compatibility for cache_result

**Conflicts with main**:
- requirements.txt: Version pinning vs minimum versions
- entities.py: Different implementation approaches
- nerdgraph_client.py: Partial implementation already in main

### PR #3: Add documentation search capability  
**Status**: OPEN  
**Key Changes**:
1. Add DocsCache class for cloning/searching New Relic docs
2. Add DocsPlugin to expose documentation search tools
3. Update README to mention documentation search feature
4. Extend tests for DocsPlugin

**Conflicts with main**:
- Depends on PR #2 changes
- entities.py formatting changes

## Merge Strategy

### Phase 1: Extract and Apply Non-Conflicting Changes

1. **Documentation Search Feature (from PR #3)**
   - Create `core/docs_cache.py` 
   - Create `features/docs.py`
   - Update README to include docs feature
   - Add gitpython dependency (already in requirements.txt)

2. **Plugin Unloading Enhancement (from PR #2)**
   - Update `plugin_manager.py` unload_plugin method
   - Already have unregister method in ServiceRegistry

3. **Connection Pool Reference Counting (from PR #2)**
   - Enhance NerdGraphClient with proper ref counting
   - Add pool_key tracking
   - Update close() method

### Phase 2: Resolve Conflicts

1. **Requirements.txt**
   - Keep minimum version approach from main
   - Ensure all dependencies from PRs are included
   - Document version compatibility in README

2. **entities.py**
   - Keep the comprehensive implementation from main
   - Apply formatting fixes if needed
   - Ensure backwards compatibility

### Phase 3: Testing and Validation

1. Run comprehensive test suite
2. Validate all plugins load correctly
3. Test cleanup and unloading functionality
4. Verify documentation search works

## Implementation Order

1. Create feature branch from main
2. Apply documentation search feature (new files, no conflicts)
3. Enhance plugin unloading in plugin_manager.py
4. Update NerdGraphClient with connection pool ref counting
5. Update README and documentation
6. Create comprehensive tests
7. Submit as single consolidated PR

## Benefits of This Approach

1. **Clean History**: Single PR instead of multiple conflicting ones
2. **Comprehensive Testing**: Test all changes together
3. **No Breaking Changes**: Maintain backwards compatibility
4. **Better Integration**: Features work well with our enhanced architecture
5. **Documentation**: Update all docs in one go