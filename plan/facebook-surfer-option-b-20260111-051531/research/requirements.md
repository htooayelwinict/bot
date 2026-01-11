# Requirements: Facebook Surfer Agent

**Source:** PRD-deepagents-option-b.md

---

## User Requirements

### Functional Requirements

1. **Tool Conversion (22 tools)**
   - Convert all TypeScript MCP tools to Python LangChain tools
   - Maintain exact functionality and input/output schemas
   - Use Pydantic for validation
   - Follow LangChain `@tool` decorator pattern

2. **Session Management**
   - Port from `src/automation/human-in-loop-login.ts`
   - Support Facebook profile persistence in `./profiles/`
   - Automatic lock file cleanup (SingletonLock, SingletonSocket)
   - 3-minute manual login window with HITL
   - Session validation using `[aria-label*="Account"]` selectors

3. **Vision Integration**
   - GPT-4o-based UI analysis tool
   - Screenshot capture before actions
   - Element detection when CSS selectors fail
   - Base64 image encoding for API

4. **Agent Orchestration**
   - Single DeepAgent using `create_deep_agent()`
   - All 22 tools registered and available
   - System prompt for Facebook user behavior
   - LangGraph for execution

5. **LOT Memory**
   - ChromaDB for vector storage
   - Store successful task patterns
   - Semantic search for similar patterns
   - Recall during planning

6. **HITL (Human-in-the-Loop)**
   - Only for Facebook login
   - `interrupt_on` configuration for login tool
   - Checkpointer for pause/resume
   - Clear approval prompts

### Non-Functional Requirements

- **Performance:** Vision API calls < 5s
- **Reliability:** Session persistence across restarts
- **Security:** Credentials via .env only
- **Maintainability:** Follow TypeScript patterns
- **Testability:** Unit tests for each tool

## Acceptance Criteria

### Phase 1: Foundation
- [ ] Python project installs without errors
- [ ] Playwright launches Chrome with stealth args
- [ ] Session persists to `./profiles/bot-facebook/`
- [ ] 5 core tools work: navigate, click, type, screenshot, page_info
- [ ] HITL login completes in < 3 min

### Phase 2: Vision
- [ ] `vision_analyze_ui` tool integrated
- [ ] Screenshot saves to `./screenshots/`
- [ ] GPT-4o returns element locations
- [ ] Falls back to vision when selectors fail

### Phase 3: Agent Assembly
- [ ] DeepAgent creates without errors
- [ ] All 22 tools registered
- [ ] Agent accepts natural language tasks
- [ ] Executes multi-step plans

### Phase 4: LOT Memory
- [ ] ChromaDB persists to `./memory/`
- [ ] Patterns store after success
- [ ] Similar patterns recall on new tasks
- [ ] Memory influences tool selection

### Phase 5: Integration
- [ ] E2E test: Login → Post → Comment
- [ ] Docker container builds/runs
- [ ] Environment config via `.env`
- [ ] Documentation complete

## Constraints

1. **Timeline:** 5-9 days MVP
2. **Budget:** Vision API costs < $50/day
3. **Compatibility:** Python 3.11+
4. **Dependencies:** Pin deepagents version
5. **Facebook:** Must follow ToS (no spam)

## User Stories

1. **As a user**, I want to say "Post a hello message on my timeline" and have the agent do it autonomously
2. **As a user**, I want the agent to remember how to navigate Facebook so it gets faster over time
3. **As a user**, I want to only log in once and have the session persist
4. **As a user**, I want the agent to show me what it's doing via screenshots
5. **As a developer**, I want to extend the agent with new tools easily

## Edge Cases

- Facebook UI changes (vision fallback)
- Session expiration (auto-re-login)
- Network failures (retry logic)
- Rate limiting (human-like delays)
- Modal dialogs (auto-dismiss)
- Multi-factor auth (HITL)
