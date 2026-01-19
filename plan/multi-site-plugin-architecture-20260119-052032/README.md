# Plan: Multi-Site Plugin Architecture

**Created:** 2025-01-19 05:20:32
**Status:** Planning
**Priority:** High

## Summary

Refactor FacebookSurferAgent into a multi-site web crawler with plugin architecture. Enable support for Facebook, Twitter, LinkedIn, and generic sites through extensible adapter system while maintaining backward compatibility.

**Current State:** Single-site Facebook agent with monolithic architecture
**Target State:** Multi-site crawler with pluggable site adapters

## Goals

### Primary Goal
Enable the web automation agent to support multiple websites (Facebook, Twitter, LinkedIn, etc.) through a plugin architecture while maintaining backward compatibility with existing Facebook functionality.

### Secondary Goals
- Reduce coupling between site-specific logic and core automation framework
- Enable third-party developers to create site adapters without modifying core code
- Standardize configuration management using Pydantic V2
- Implement async-first lifecycle management with structured concurrency
- Provide clear upgrade path for existing FacebookSurferAgent users

## Scope

### In Scope
- Plugin architecture with Protocol-based interfaces
- PluginLoader with dual discovery (entry points + directory scanning)
- Configuration system using pydantic-settings
- Async lifecycle management with asyncio.TaskGroup
- Tool registry for LangChain integration
- Migration of Facebook code to FacebookAdapter
- Template/example for creating new adapters
- Documentation for plugin developers
- Comprehensive test coverage

### Out of Scope
- Rewrite of existing browser tools (keep as-is)
- Changes to LangGraph/DeepAgents integration
- New automation features (focus on architecture only)
- UI/dashboard for plugin management
- Plugin marketplace/distribution
- Hot-reloading for development (future enhancement)

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing Facebook functionality | High | Medium | Keep original FacebookSurferAgent, create parallel MultiSiteAgent, thorough testing |
| Plugin API changes requiring frequent migrations | High | Low | Version adapters, clear deprecation policy, comprehensive docs |
| Performance degradation from abstraction layers | Medium | Low | Profile before/after, lazy loading, minimize overhead |
| Complex async lifecycle causing deadlocks | High | Medium | Use Python 3.11+ TaskGroup, timeout handling, error isolation |
| Configuration errors preventing plugin loading | Medium | Medium | Pydantic validation, clear error messages, schema examples |

## Phases Overview

| Phase | Description | Est. Effort | Dependencies |
|-------|-------------|-------------|--------------|
| 1 | Core Architecture (Protocols, PluginLoader, Config) | 3-4 days | None |
| 2 | Facebook Adapter Migration | 2-3 days | Phase 1 |
| 3 | Multi-Site Agent with LangGraph | 2-3 days | Phase 1, 2 |
| 4 | Additional Adapters (Twitter, Generic) | 2 days | Phase 1, 2 |
| 5 | Testing, Documentation, Polish | 2-3 days | Phase 1-4 |

**Total Estimated Effort:** 11-15 days

## Files to Create

### Core Architecture
- `src/core/protocols.py` — Protocol definitions (SiteAdapter, CrawlConfig, etc.)
- `src/core/plugin_loader.py` — Plugin discovery and loading
- `src/core/tool_registry.py` — LangChain tool management
- `src/core/lifecycle.py` — Async lifecycle with TaskGroup
- `src/core/config/settings.py` — pydantic-settings configuration
- `src/core/config/dynamic.py` — Dynamic config schemas

### Adapters
- `src/plugins/facebook/adapter.py` — Facebook adapter (migrated from existing code)
- `src/plugins/twitter/adapter.py` — Twitter adapter (new)
- `src/plugins/generic/adapter.py` — Generic/fallback adapter (new)

### Agents
- `src/agents/multi_site_agent.py` — New multi-site agent
- `src/agents/facebook_surfer.py` — Keep for backward compatibility

### Configuration
- `config/sites.yaml` — Site-specific configurations
- `config/.env.example` — Environment variable template

### Tests
- `tests/test_protocols.py` — Protocol tests
- `tests/test_plugin_loader.py` — Plugin loading tests
- `tests/test_adapters/test_facebook.py` — Facebook adapter tests
- `tests/test_adapters/test_twitter.py` — Twitter adapter tests
- `tests/test_multi_site_agent.py` — Integration tests

### Documentation
- `docs/PLUGIN_DEVELOPMENT.md` — Plugin development guide
- `docs/MIGRATION_GUIDE.md` — Migration from FacebookSurferAgent
- `README.md` — Update with multi-site support

## Success Criteria

- [ ] FacebookSurferAgent continues to work without changes
- [ ] New MultiSiteAgent can crawl Facebook using FacebookAdapter
- [ ] TwitterAdapter successfully implemented and tested
- [ ] GenericAdapter handles unknown sites
- [ ] Plugin loading from entry points works
- [ ] Plugin loading from directory scanning works
- [ ] Configuration via pydantic-settings works
- [ ] Async lifecycle properly initializes and shutdowns
- [ ] All existing tests pass
- [ ] New test coverage > 80%
- [ ] Documentation complete and clear

## Next Steps

1. Review consolidated plan in `plan.md`
2. Review phase breakdown in `phases/` folder
3. Run `/code plan/multi-site-plugin-architecture-20260119-052032` to start implementation
