# Documentation Migration Guide

## Overview

This guide helps consolidate and organize the project documentation to eliminate duplication and improve clarity.

## Current Issues

### 1. Duplicate Files
These files contain overlapping or duplicate content:

| Root File | Docs File | Action |
|-----------|-----------|---------|
| `ARCHITECTURE.md` | `docs/ARCHITECTURE.md` | Keep docs version, delete root |
| `IMPLEMENTATION_LOG.md` | `docs/IMPLEMENTATION_LOG.md` | Merge into `docs/IMPLEMENTATION_STATUS.md` |
| `TRACK1_PROGRESS.md` | `docs/track1-discovery-core.md` | Merge into `docs/IMPLEMENTATION_STATUS.md` |
| `TRACK1_COMPLETION_SUMMARY.md` | - | Archive or merge into status |

### 2. Scattered Track Documentation
Consolidate all track-related docs into `docs/IMPLEMENTATION_STATUS.md`:
- `TRACK1_PROGRESS.md`
- `TRACK1_COMPLETION_SUMMARY.md`
- `docs/TRACK2_PROGRESS.md`
- `docs/track2-week1-summary.md`
- `docs/track2-week2-summary.md`

### 3. Inconsistent Status Reporting
- Multiple files report different completion percentages
- No single source of truth for project status

## Recommended Structure

```
mcp-server-newrelic/
├── README.md                    # Project overview and quick start
├── CLAUDE.md                    # AI assistant instructions
├── LICENSE                      # License file
├── .env.example                 # Example configuration
│
├── docs/
│   ├── ARCHITECTURE.md          # System architecture (consolidated)
│   ├── API_REFERENCE.md         # Complete API documentation
│   ├── DEPLOYMENT.md            # Production deployment guide
│   ├── DEVELOPMENT.md           # Developer guide
│   ├── IMPLEMENTATION_STATUS.md # Single source for progress
│   ├── QUICKSTART.md           # 5-minute setup guide
│   └── archives/               # Old/duplicate docs (for reference)
│       ├── track1-progress/
│       ├── track2-progress/
│       └── legacy/
│
├── pkg/                        # Go packages with inline docs
├── features/                   # Python features with docstrings
├── tests/README.md            # Testing guide
└── scripts/README.md          # Script documentation
```

## Migration Steps

### Step 1: Archive Duplicates
```bash
# Create archive directory
mkdir -p docs/archives/{track1-progress,track2-progress,legacy}

# Move duplicate files
mv ARCHITECTURE.md docs/archives/legacy/
mv IMPLEMENTATION_LOG.md docs/archives/legacy/
mv TRACK1_*.md docs/archives/track1-progress/
mv docs/track2-week*.md docs/archives/track2-progress/
```

### Step 2: Update Cross-References
Search and replace file references:
- `ARCHITECTURE.md` → `docs/ARCHITECTURE.md`
- `track1-discovery-core.md` → `docs/IMPLEMENTATION_STATUS.md#track-1`
- Track-specific docs → `docs/IMPLEMENTATION_STATUS.md`

### Step 3: Consolidate Content
1. Merge all track progress into `IMPLEMENTATION_STATUS.md`
2. Update completion percentages to be consistent
3. Remove conflicting information

### Step 4: Update README Links
Ensure README.md links point to correct locations:
```markdown
- **[Architecture Overview](./docs/ARCHITECTURE.md)**
- **[Implementation Status](./docs/IMPLEMENTATION_STATUS.md)**
```

## Content Guidelines

### IMPLEMENTATION_STATUS.md Structure
```markdown
# Implementation Status

## Overview
- Overall progress percentage
- Last updated date

## Track Summary Table
| Track | Progress | Status | Details |

## Track 1: Discovery Core
### Completed ✅
### In Progress 🚧
### Pending ⏳

## Track 2: Interface Layer
...

## Known Issues
## Upcoming Milestones
## Action Items
```

### Version Control
- Keep archived docs in git history
- Add redirect notes in old locations
- Update any external documentation links

## Benefits After Migration

1. **Single Source of Truth**: One place for implementation status
2. **Clear Navigation**: Logical documentation structure
3. **Reduced Confusion**: No conflicting information
4. **Easier Maintenance**: Less duplication to update
5. **Better Discoverability**: Clear hierarchy

## Maintenance Guidelines

### Going Forward
1. **No Root-Level Docs**: Keep all documentation in `docs/`
2. **Regular Reviews**: Monthly documentation audits
3. **Automated Checks**: Add CI checks for broken links
4. **Versioning**: Tag documentation with releases

### Documentation Standards
- Use relative links within docs
- Include "Last Updated" timestamps
- Follow consistent formatting
- Keep technical details in code comments

## Tools for Migration

### Find Broken Links
```bash
# Install markdown-link-check
npm install -g markdown-link-check

# Check all markdown files
find . -name "*.md" -exec markdown-link-check {} \;
```

### Find Duplicates
```bash
# Find similar content
grep -r "Track 1" --include="*.md" . | sort | uniq -c
```

### Update References
```bash
# Update all references
find . -name "*.md" -exec sed -i 's|ARCHITECTURE.md|docs/ARCHITECTURE.md|g' {} \;
```

## Checklist

- [ ] Archive duplicate files
- [ ] Update IMPLEMENTATION_STATUS.md with all track info
- [ ] Fix all cross-references
- [ ] Update README.md links
- [ ] Remove conflicting information
- [ ] Add redirects for moved files
- [ ] Update external documentation
- [ ] Run link checker
- [ ] Commit with clear message