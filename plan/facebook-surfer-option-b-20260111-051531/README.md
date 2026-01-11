# Plan: Facebook Surfer Agent (Option B)

**Created:** 2026-01-11
**Approach:** Single DeepAgent with Vision Tool Wrapper
**Timeline:** 5-9 days MVP

---

## Summary

Convert 22 TypeScript MCP Playwright tools to Python LangChain tools and build a DeepAgent that autonomously performs Facebook tasks using GPT-4o vision for UI understanding and ChromaDB for LOT (Learning Over Time) memory.

## Goals

- [ ] Convert all 22 TypeScript MCP tools to Python LangChain tools
- [ ] Implement session management (login + persistence) using proven TS patterns
- [ ] Integrate GPT-4o vision tool for UI analysis
- [ ] Build single DeepAgent with `create_deep_agent()` from deepagents library
- [ ] Implement LOT memory via ChromaDB/LangGraph Store
- [ ] Support HITL (Human-in-the-Loop) for Facebook login only
- [ ] Docker containerization for deployment

## Scope

**In Scope:**
- All 22 tools converted (navigation, interaction, forms, utilities, browser)
- Session management with Facebook profiles
- Vision-based UI understanding via GPT-4o
- LOT memory for pattern storage/recall
- HITL for Facebook login
- E2E testing with real Facebook tasks
- Docker containerization

**Out of Scope:**
- Multi-agent delegation
- Advanced anti-detection bypasses
- Production-scale deployment
- Facebook API integration (browser-only)

## Risk Assessment

| Risk | Level | Impact | Mitigation |
|------|-------|--------|------------|
| Facebook anti-bot detection | High | Blocking | Reuse TS stealth mode, human-like delays |
| Python conversion bugs | Medium | Broken tools | Test individually, keep TS reference |
| Vision API costs/latency | Medium | Performance | Cache results, use selectively |
| DeepAgents API changes | Low | Breaking changes | Pin dependency versions |
| Session persistence | High | Lost sessions | Reuse proven TS patterns |
| LOT memory quality | Low | Poor patterns | Validate before storage, score patterns |

## Phase Overview

| Phase | Name | Objective | Est. Effort |
|-------|------|-----------|-------------|
| 1 | Foundation | Python project setup, session management, 5 core tools | 1-2 days |
| 2 | Vision Integration | GPT-4o vision tool, screenshot capture | 1-2 days |
| 3a | Tool Conversion | Convert remaining 17 tools (type, select, hover, press_key, forms, utilities, browser) | 4-6 hours |
| 3b | Agent Assembly | ToolRegistry, DeepAgent, system prompt, CLI | 4-6 hours |
| 4 | LOT Memory | ChromaDB pattern storage, recall tools | 1-2 days |
| 5 | Integration & Testing | E2E testing, HITL, Docker | 1-2 days |

**Total Estimated Effort:** 5-9 days

## Progress

- [x] **Phase 1: Foundation** ✅ Completed 2026-01-12
- [x] **Phase 2: Vision Integration** ✅ Completed 2026-01-12
- [ ] Phase 3a: Tool Conversion
- [ ] Phase 3b: Agent Assembly
- [ ] Phase 4: LOT Memory
- [ ] Phase 5: Integration & Testing

## Files to Modify

**New Python Project:**
- `src/agents/facebook_surfer.py` - Main agent
- `src/tools/` - All 22 converted tools
- `src/session/playwright_session.py` - Session management
- `src/main.py` - Entry point
- `pyproject.toml` - Dependencies
- `Dockerfile` - Containerization

**Reference TypeScript (read-only):**
- `src/automation/human-in-loop-login.ts`
- `src/mcp-tools/tools/*.ts`
- `src/demo-ai-agent.ts`

## Key Technical Decisions

1. **Single DeepAgent** - Not multi-agent delegation (simpler, faster MVP)
2. **GPT-4o Vision** - For UI element detection when selectors fail
3. **ChromaDB** - For LOT memory (vector similarity search)
4. **HITL Login Only** - All other actions autonomous
5. **Session Reuse** - Port proven TS patterns to Python

## Dependencies

```txt
deepagents>=0.1.0
langchain>=0.3.0
langchain-openai>=0.2.0
langgraph>=0.2.0
playwright>=1.48.0
chromadb>=0.5.0
openai>=1.54.0
pydantic>=2.0.0
python-dotenv>=1.0.0
```

## Success Metrics

- [ ] Agent navigates Facebook and logs in with HITL
- [ ] Performs basic tasks (post, comment, like) via NL
- [ ] Vision identifies UI elements 90%+ accuracy
- [ ] LOT recalls and reuses patterns
- [ ] Session persists across restarts
- [ ] All 22 tools converted successfully
- [ ] Handles 3+ distinct Facebook task types
- [ ] Vision fallback works when selectors fail

---

## Documentation

| Document | Description |
|----------|-------------|
| [plan.md](plan.md) | ⭐ Consolidated implementation plan (all phases) |
| [research/react-workflow.md](research/react-workflow.md) | How the agent reasons and acts (ReAct pattern) |
| [research/requirements.md](research/requirements.md) | User requirements and acceptance criteria |
| [research/existing-code.md](research/existing-code.md) | TypeScript patterns to port |
| [research/references.md](research/references.md) | External docs and best practices |
