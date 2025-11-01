# Excel Differ - Project Plan and Status

**Last Updated:** 2025-11-01
**Version:** 3.0
**Status:** Phase 4 - V4 Architecture Complete

---

## Overview

Excel Differ is a modular system for converting Excel workbooks into version-control-friendly text representations, enabling meaningful diffs of Excel files. The system uses a **plugin-based architecture** with clearly defined component interfaces for maximum flexibility and extensibility.

---

## Current Status

### Phase 1: Flattener Component ✅ **COMPLETE**

**Status:** Production-ready (v2.1.0)

**Completed:**
- Core extraction engine (formulas, values, metadata, VBA, charts, tables)
- Dual-order formula extraction (by row and by column)
- Manifest generation with file hashes
- CLI interface
- Comprehensive documentation
- Build scripts and virtual environment setup

**Location:** [components/flattener/](../components/flattener/)

---

### Phase 2: Plugin Architecture Design 🔄 **IN PROGRESS**

**Status:** Interface design complete, implementation pending

**Goal:** Create a loosely coupled, pluggable architecture where components can be swapped, extended, and independently developed.

**Design Decisions:**
1. **Separation of Concerns:** Split "getting files" (Source) from "uploading results" (Destination)
2. **Interface-Based:** All components implement abstract interfaces
3. **No Optional Components:** All components required, use NoOp implementations to disable
4. **Configuration-Driven:** YAML config determines which implementations to use
5. **Multiple Implementations:** Support API-based (Bitbucket) and local (filesystem, GitPython) implementations

**Components Defined:**

| Component | Purpose | Status |
|-----------|---------|--------|
| **Source** | Get files to process (Bitbucket, local, GitHub, S3) | Interface designed |
| **Destination** | Upload processed results (Bitbucket, local, GitHub, S3) | Interface designed |
| **Converter** | Convert Excel formats (.xlsb → .xlsm) | Interface designed |
| **Flattener** | Flatten Excel to text | ✅ Implemented, needs wrapper |
| **Orchestrator** | Coordinate workflow | Interface designed |

**Key Architectural Patterns:**
- Strategy Pattern for pluggable implementations
- Dependency Injection (all components passed to orchestrator)
- Factory Pattern for creating component instances from config

---

## Phase Breakdown

### Phase 2.1: Core Interfaces and Registry 📋 **NEXT**

**Timeline:** 1 week

**Tasks:**
- [ ] Create `components/core/interfaces.py` with all interface definitions
- [ ] Create `components/core/config.py` with configuration classes
- [ ] Create `components/core/plugin_registry.py` for component registration
- [ ] Create `components/core/config_loader.py` to load YAML config
- [ ] Write interface documentation with examples
- [ ] Create base test framework for interfaces

**Deliverables:**
- Complete interface definitions
- Configuration data classes
- Plugin registry system
- Configuration loader
- Documentation: COMPONENT_SPECIFICATIONS.md

---

### Phase 2.2: NoOp Implementations 📋 **PLANNED**

**Timeline:** 3 days

**Tasks:**
- [ ] Implement `NoOpConverter` (explicit no-conversion)
- [ ] Implement `NoOpSource` (for testing/debugging)
- [ ] Implement `NoOpDestination` (for testing/debugging)
- [ ] Create test suite for NoOp components
- [ ] Document usage patterns

**Deliverables:**
- Working NoOp implementations
- Tests confirming interface compliance
- Usage examples

---

### Phase 2.3: Flattener Plugin Wrapper 📋 **PLANNED**

**Timeline:** 3 days

**Tasks:**
- [ ] Create `components/flattener/src/flattener_plugin.py`
- [ ] Implement `FlattenerInterface` wrapping existing `Flattener` class
- [ ] Add configuration mapping
- [ ] Create tests
- [ ] Update documentation

**Deliverables:**
- `OpenpyxlFlattener` implementing `FlattenerInterface`
- Integration tests
- Updated flattener README

---

### Phase 2.4: Orchestrator Core 📋 **PLANNED**

**Timeline:** 1 week

**Tasks:**
- [ ] Implement `Orchestrator` class accepting all components
- [ ] Implement main workflow logic
- [ ] Implement synchronisation state management
- [ ] Add error handling and recovery
- [ ] Create comprehensive tests with mock components
- [ ] Write orchestrator documentation

**Deliverables:**
- Working orchestrator
- Full test coverage
- Orchestrator documentation

---

### Phase 2.5: Bitbucket Source Implementation 📋 **PLANNED**

**Timeline:** 1-2 weeks

**Tasks:**
- [ ] Implement `BitbucketSource` using Bitbucket API
- [ ] Implement `get_changed_files()` with commit comparison
- [ ] Implement `download_file()` via API
- [ ] Implement pattern matching (include/exclude)
- [ ] Handle authentication with tokens
- [ ] Implement depth-based sync for first run
- [ ] Create comprehensive tests (using mocked API)
- [ ] Document Bitbucket-specific configuration

**Deliverables:**
- Working Bitbucket source component
- API integration tests
- Configuration examples
- Bitbucket setup guide

---

### Phase 2.6: Bitbucket Destination Implementation 📋 **PLANNED**

**Timeline:** 1 week

**Tasks:**
- [ ] Implement `BitbucketDestination` using Bitbucket API
- [ ] Implement `upload_file()` via API
- [ ] Implement `upload_directory()` with multipart upload
- [ ] Implement `save_sync_state()` to commit state file
- [ ] Handle authentication
- [ ] Create tests (using mocked API)
- [ ] Document upload strategies

**Deliverables:**
- Working Bitbucket destination component
- Upload tests
- Documentation

---

### Phase 2.7: Local Implementations 📋 **PLANNED**

**Timeline:** 1 week

**Tasks:**
- [ ] Implement `LocalFolderSource`
- [ ] Implement `LocalFolderDestination`
- [ ] Implement file watching for change detection
- [ ] Implement timestamp-based sync
- [ ] Create tests
- [ ] Document local workflow use cases

**Deliverables:**
- Local source and destination components
- Tests
- Documentation for local-only workflows

---

### Phase 2.8: End-to-End Integration 📋 **PLANNED**

**Timeline:** 1 week

**Tasks:**
- [ ] Create main entry point (`main.py`)
- [ ] Implement component factory from config
- [ ] Create example configurations for common scenarios
- [ ] End-to-end integration tests
- [ ] Performance testing
- [ ] Create deployment guide
- [ ] Create troubleshooting guide

**Deliverables:**
- Working system with all components
- Example configs
- Complete integration tests
- Deployment documentation

---

## Phase 3: Converter Component 📋 **FUTURE**

**Timeline:** 1-2 weeks

**Goal:** Implement Excel format conversion (primarily .xlsb → .xlsm)

**Implementations Planned:**
- `WindowsExcelConverter` (uses COM automation on Windows)
- `LibreOfficeConverter` (uses LibreOffice headless on Linux)
- Platform auto-detection

**Tasks:**
- [ ] Design converter interface details
- [ ] Implement Windows converter (COM)
- [ ] Implement LibreOffice converter
- [ ] Add format detection logic
- [ ] Create tests for both implementations
- [ ] Document platform-specific setup

---

## Phase 4: Additional Source/Destination Implementations 📋 **FUTURE**

**Timeline:** 2-3 weeks

**Potential Implementations:**
- GitHub source/destination (GitHub API)
- GitLab source/destination (GitLab API)
- GitPython source/destination (local git)
- S3 source/destination (AWS)
- Azure Blob source/destination

**Prioritisation:** Based on user needs

---

## Phase 5: Differ Component 📋 **FUTURE**

**Timeline:** 2-3 weeks

**Goal:** Compare two flattened outputs and generate structured diffs

**Tasks:**
- [ ] Design differ interface
- [ ] Implement file-level diff detection
- [ ] Implement cell-level diff for sheets
- [ ] Implement formula diff highlighting
- [ ] Generate structured JSON diff
- [ ] Generate unified text diff
- [ ] Create diff statistics and summary
- [ ] Build CLI interface
- [ ] Create tests
- [ ] Write documentation

---

## Key Decisions Made

### Decision 1: Separate Source and Destination Components
**Date:** 2025-11-01
**Rationale:** "Getting files" and "uploading results" are fundamentally different concerns with different implementations (Git, local, S3, HTTP). Separating them provides maximum flexibility.

### Decision 2: All Components Required (No Optionals)
**Date:** 2025-11-01
**Rationale:** Explicit is better than implicit. Use NoOp implementations (e.g., `NoOpConverter()`) to disable features rather than `None` or optional parameters.

### Decision 3: Depth-Based Initial Sync
**Date:** 2025-11-01
**Rationale:** When no sync state exists, `depth` parameter controls how far back to process: 0=do nothing, 1=last commit, 2=last 2 commits, etc. Prevents accidental full-history processing.

### Decision 4: Configuration-Driven Component Selection
**Date:** 2025-11-01
**Rationale:** YAML configuration specifies which implementation to use for each component. Enables switching implementations without code changes.

### Decision 5: Include/Exclude Patterns
**Date:** 2025-11-01
**Rationale:** Users need fine-grained control over which files to process. Include patterns define what to process, exclude patterns define exceptions.

---

## Success Criteria

### Phase 2 Success Criteria:
- ✅ All component interfaces clearly defined and documented
- ⏳ Orchestrator can coordinate any combination of components
- ⏳ Can process files from Bitbucket and save locally
- ⏳ Can process files from local folder and save to Bitbucket
- ⏳ Can process files from Bitbucket and save to same repo
- ⏳ Depth-based sync works correctly for initial runs
- ⏳ Include/exclude patterns work correctly
- ⏳ All components have >80% test coverage
- ⏳ Documentation complete and clear

### Overall Success Criteria:
- Excel files can be tracked in version control with meaningful diffs
- System works reliably in automated workflows (CI/CD)
- Components can be independently developed and tested
- New source/destination types can be added easily
- Configuration is clear and maintainable
- Errors are handled gracefully with clear messages
- Performance is acceptable (<5 minutes for typical workbook)

---

## Risks and Mitigations

### Risk 1: Bitbucket API Rate Limiting
**Mitigation:** Implement caching, batch operations, use local git clone as fallback

### Risk 2: Large File Uploads via API
**Mitigation:** Implement chunked uploads, add timeout handling, document size limits

### Risk 3: Complex Configuration
**Mitigation:** Provide example configs for common scenarios, validation with helpful errors

### Risk 4: Platform Differences (Windows vs Linux)
**Mitigation:** Abstract platform-specific code behind interfaces, test on both platforms

---

## Open Questions

### To Be Decided:
1. Should we support GitPython as alternative to API-based implementations?
   - **Answer Pending:** Yes, but lower priority than Bitbucket API

2. How to handle authentication for multiple repos?
   - **Current:** Separate tokens in config for source and destination

3. Should orchestrator support parallel file processing?
   - **Current:** No, process sequentially for now

4. How to handle large repositories with many Excel files?
   - **To Explore:** Incremental processing, filtering by path

---

## Dependencies

### Development Dependencies:
- Python 3.9+
- openpyxl (flattener)
- lxml (flattener)
- oletools (flattener VBA)
- click (CLI)
- pyyaml (config)
- requests (API calls)
- pytest (testing)

### Runtime Dependencies (Minimal):
- Python 3.9+
- Dependencies listed in requirements.txt

### Optional Dependencies:
- LibreOffice (for converter on Linux)
- Win32com (for converter on Windows)
- GitPython (for local git implementation)

---

## Timeline Summary

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1: Flattener | 4 weeks | ✅ Complete |
| Phase 2.1: Core Interfaces | 1 week | 📋 Next |
| Phase 2.2: NoOp Implementations | 3 days | 📋 Planned |
| Phase 2.3: Flattener Wrapper | 3 days | 📋 Planned |
| Phase 2.4: Orchestrator Core | 1 week | 📋 Planned |
| Phase 2.5: Bitbucket Source | 1-2 weeks | 📋 Planned |
| Phase 2.6: Bitbucket Destination | 1 week | 📋 Planned |
| Phase 2.7: Local Implementations | 1 week | 📋 Planned |
| Phase 2.8: Integration | 1 week | 📋 Planned |
| **Phase 2 Total** | **6-7 weeks** | 🔄 In Progress |
| Phase 3: Converter | 1-2 weeks | 📋 Future |
| Phase 4: Additional Sources | 2-3 weeks | 📋 Future |
| Phase 5: Differ | 2-3 weeks | 📋 Future |

**Estimated Completion:** Phase 2 by end of December 2025

---

## How to Use This Document

**For Contributors:**
- Check current phase status
- Review next tasks
- Understand architectural decisions
- See what's planned ahead

**For Project Manager:**
- Track progress against timeline
- Identify blockers
- Assess risk
- Communicate status

**For Users:**
- Understand what's available now
- See what's coming next
- Know when features will be ready

---

## References

- [ARCHITECTURE_V3.md](ARCHITECTURE_V3.md) - Complete architecture design
- [COMPONENT_SPECIFICATIONS.md](COMPONENT_SPECIFICATIONS.md) - Component interface specs
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - How to deploy and run
- [../components/flattener/README.md](../components/flattener/README.md) - Flattener user guide

---

**END OF PROJECT PLAN**
