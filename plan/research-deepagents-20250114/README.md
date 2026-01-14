# DeepAgents Research

**Date:** 2025-01-14  
**Framework Version:** 0.3.5  
**Status:** Complete

## Contents

1. **findings.md** - Comprehensive documentation on DeepAgents framework
   - Core concepts and architecture
   - Complete API reference
   - Configuration examples
   - Streaming and debugging guide
   - Skills system documentation
   - Best practices

2. **quick-reference.md** - Quick code examples and patterns
   - Agent creation
   - Stream modes
   - Skills setup
   - Human-in-the-loop
   - Subagents
   - Common patterns

## Key Takeaways

- DeepAgents is built on LangChain + LangGraph
- Provides pre-configured middleware stack
- Default model: Claude Sonnet 4.5
- Supports custom LLM configs (base_url, api_key, headers)
- Rich streaming API: `astream()` and `astream_events()`
- Progressive disclosure skills system
- Built-in subagent support

## Source Analysis

Research based on:
- DeepAgents 0.3.5 source code (installed in .venv)
- Project integration: `src/agents/facebook_surfer.py`
- LangChain/LangGraph official documentation

## Usage in Project

See `src/agents/facebook_surfer.py` for:
- OpenRouter integration with custom base_url
- Skills middleware for Facebook automation
- Playwright tool integration
- Stream methods for real-time feedback
