# Plan: Facebook Surfer Agent (Option B Implementation)

**Created:** 2026-01-11
**Approach:** Single DeepAgent with Vision Tool Wrapper
**Target:** MVP in 5-9 days

---

## Context

Converting 22 TypeScript MCP Playwright tools to Python LangChain tools and building a DeepAgent that autonomously performs Facebook tasks using GPT-4o vision for UI understanding and ChromaDB for LOT (Learning Over Time) memory.

**Key Challenge:** Porting proven TypeScript patterns (session management, stealth mode, tool execution) to Python while integrating with LangChain's DeepAgents framework.

**Success Definition:** Agent can log in via HITL, execute natural language Facebook tasks (post, comment, search), learn from patterns, and persist across restarts.

**📖 Agent Behavior:** See [research/react-workflow.md](research/react-workflow.md) for detailed ReAct loop explanation and example scenarios.

---

## Existing Code Patterns to Follow

### Session Management (`src/automation/human-in-loop-login.ts`)

**Browser Args (Stealth Mode):**
```typescript
const BROWSER_ARGS = [
  '--no-sandbox',
  '--disable-setuid-sandbox',
  '--disable-blink-features=AutomationControlled',
  '--disable-web-security',
  // ... more anti-detection args
];
```

**Login Detection:**
```typescript
const LOGGED_IN_SELECTORS = [
  '[aria-label*="Account"]',
  '[data-testid="bluebar_profile_root"]',
  'a[href*="/me"][role="link"]'
];
```

**Python Conversion Pattern:**
```python
from playwright.sync_api import sync_playwright

class PlaywrightSession:
    def start_login(self) -> bool:
        # Clean lock files
        for lock in ['SingletonLock', 'SingletonSocket']:
            os.remove(os.path.join(self.profile_path, lock))

        # Launch persistent context
        with sync_playwright() as p:
            self.context = p.chromium.launch_persistent_context(
                self.profile_path,
                headless=False,
                args=BROWSER_ARGS,
                slow_mo=100,
                viewport={'width': 1920, 'height': 1080}
            )

            return self._wait_for_login()
```

### Tool Pattern (`src/mcp-tools/tools/`)

**TypeScript Tool:**
```typescript
export class NavigateTool extends BaseMCPTool {
  definition = {
    name: 'browser_navigate',
    description: 'Navigate to a specific URL...',
    inputSchema: {
      type: 'object',
      properties: {
        url: { type: 'string', description: 'The URL to navigate to' }
      },
      required: ['url']
    }
  };

  protected async _execute(args: any, context: MCPContext) {
    const { page } = context;
    await page.goto(args.url);
    return { content: [{ type: 'text', text: `Navigated to ${args.url}` }] };
  }
}
```

**Python LangChain Conversion:**
```python
from pydantic import BaseModel, Field
from langchain.tools import tool

class NavigateArgs(BaseModel):
    url: str = Field(description="The URL to navigate to")

@tool
def browser_navigate(args: NavigateArgs) -> str:
    """Navigate to a specific URL. Waits for the page to load before returning."""
    page = get_current_page()
    page.goto(args.url)
    return f"Navigated to {args.url}"
```

### Agent Orchestration (`src/demo-ai-agent.ts`)

**TypeScript Pattern:**
```typescript
class AIAgent {
  async executeTask(taskDescription: string) {
    const plan = this.createPlan(taskDescription);
    for (const step of plan) {
      const result = await this.executeTool(step);
    }
  }
}
```

**Python DeepAgent Pattern:**
```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="gpt-4o",
    tools=[browser_navigate, browser_click, vision_analyze_ui],
    store=chroma_store,
    checkpointer=checkpointer
)

result = agent.invoke({"messages": [("user", "Post a hello message")]})
```

---

## Phase Overview

| # | Name | Objective | Est. Effort |
|---|------|-----------|-------------|
| 1 | Foundation | Python setup, session management, 5 core tools | 1-2 days |
| 2 | Vision Integration | GPT-4o vision tool, screenshot capture | 1-2 days |
| 3a | Tool Conversion | Convert remaining 17 tools (type, select, hover, press_key, forms, utilities, browser) | 4-6 hours |
| 3b | Agent Assembly | ToolRegistry, DeepAgent, system prompt, CLI | 4-6 hours |
| 4 | LOT Memory | ChromaDB pattern storage | 1-2 days |
| 5 | Integration & Testing | E2E testing, HITL, Docker | 1-2 days |

**Total Estimated Effort:** 5-9 days

---

## Phase 1: Foundation

### Objective
Set up Python project, implement session management (port from TypeScript), convert 5 core tools

### Tasks

- [ ] Create Python project structure with `pyproject.toml`
- [ ] Install dependencies (deepagents, langchain, playwright, chromadb)
- [ ] Port `HumanInLoopLogin` to Python (`src/session/playwright_session.py`)
- [ ] Implement lock file cleanup, browser stealth args, login polling
- [ ] Create base tool classes with Pydantic validation
- [ ] Convert 5 core tools: navigate, back, screenshot, page_info, click
- [ ] Unit tests for session and tools

### Files to Create/Modify

| File | Action | Details |
|------|--------|---------|
| `pyproject.toml` | Create | Dependencies: deepagents, langchain, playwright, chromadb |
| `src/session/playwright_session.py` | Create | Port from `src/automation/human-in-loop-login.ts` |
| `src/tools/navigation.py` | Create | navigate, back, screenshot, page_info |
| `src/tools/interaction.py` | Create | click tool |
| `tests/test_session.py` | Create | Session management tests |

### Verification

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium
pytest tests/test_session.py -v
python -m src.session.playwright_session  # Test HITL login
```

**Expected:** Session persists to `./profiles/bot-facebook/`, 5 tools work

---

## Phase 2: Vision Integration

### Objective
Implement GPT-4o vision tool for UI analysis when selectors fail

### Tasks

- [ ] Create `vision_analyze_ui` tool with base64 encoding
- [ ] Implement prompt engineering for Facebook UI
- [ ] Add vision fallback strategy (selector → vision → selector)
- [ ] Enhance screenshot tool with caching
- [ ] Add pre-action screenshot hook
- [ ] Test vision tool with sample screenshots

### Files to Create/Modify

| File | Action | Details |
|------|--------|---------|
| `src/tools/vision.py` | Create | GPT-4o vision tool + fallback logic |
| `src/tools/base.py` | Modify | Add screenshot hook decorator |
| `tests/test_vision_tools.py` | Create | Vision tool tests |

### Verification

```bash
pip install openai pillow
python -c "
from src.tools.vision import vision_analyze_ui, VisionAnalyzeArgs
result = vision_analyze_ui(VisionAnalyzeArgs(
    task_context='Find the login button',
    screenshot_path='./screenshots/test.png'
))
print(result)
"
pytest tests/test_vision_tools.py -v
```

**Expected:** Vision returns element locations, fallback works, API latency < 5s

---

## Phase 3a: Tool Conversion

### Objective
Convert remaining 17 tools from TypeScript to Python (interaction, forms, utilities, browser)

### Tasks

**Interaction Tools** (4 remaining):
- [ ] `browser_type` - Type text into inputs
- [ ] `browser_select_option` - Dropdown selection
- [ ] `browser_hover` - Hover over elements
- [ ] `browser_press_key` - Keyboard input

**Form Tools** (3 tools):
- [ ] `browser_fill_form` - Fill multiple fields
- [ ] `browser_get_form_data` - Extract form data
- [ ] `browser_submit_form` - Submit form

**Utility Tools** (5 tools):
- [ ] `browser_wait` - Wait for conditions
- [ ] `browser_evaluate` - Execute JavaScript
- [ ] `browser_get_snapshot` - Accessibility tree
- [ ] `browser_get_network_requests` - Network log
- [ ] `browser_get_console_messages` - Console log

**Browser Tools** (5 tools):
- [ ] `browser_tabs` - Tab management
- [ ] `browser_resize` - Window resize
- [ ] `browser_handle_dialog` - Alert/confirm handling
- [ ] `browser_reload` - Page reload
- [ ] `browser_close` - Close browser/page

### Files to Create/Modify

| File | Action | Details |
|------|--------|---------|
| `src/tools/interaction.py` | Create | Type, select, hover, press_key |
| `src/tools/forms.py` | Create | Fill, get_data, submit |
| `src/tools/utilities.py` | Create | Wait, evaluate, snapshot, network, console |
| `src/tools/browser.py` | Create | Tabs, resize, dialog, reload, close |
| `tests/test_tools_conversion.py` | Create | Unit tests for all 17 tools |

### Verification

```bash
# Test each tool category
pytest tests/test_tools_conversion.py -v -k "test_interaction"
pytest tests/test_tools_conversion.py -v -k "test_forms"
pytest tests/test_tools_conversion.py -v -k "test_utilities"
pytest tests/test_tools_conversion.py -v -k "test_browser"

# Verify all tools import
python -c "
from src.tools.interaction import browser_type, browser_select_option, browser_hover, browser_press_key
from src.tools.forms import browser_fill_form, browser_get_form_data, browser_submit_form
from src.tools.utilities import browser_wait, browser_evaluate, browser_get_snapshot, browser_get_network_requests, browser_get_console_messages
from src.tools.browser import browser_tabs, browser_resize, browser_handle_dialog, browser_reload, browser_close
print('All 17 tools imported successfully')
"
```

**Expected:** All 17 tools convert with unit tests passing

**Estimated Effort:** 4-6 hours

---

## Phase 3b: Agent Assembly

### Objective
Create ToolRegistry, FacebookSurferAgent with create_deep_agent(), system prompt, CLI entry point

### Tasks

- [ ] Create ToolRegistry class with categories
- [ ] Implement FacebookSurferAgent using create_deep_agent()
- [ ] Add system prompt for Facebook user behavior
- [ ] Create CLI entry point (src/main.py)
- [ ] Test agent creation and task execution

### Files to Create/Modify

| File | Action | Details |
|------|--------|---------|
| `src/tools/registry.py` | Create | Tool registry with categories |
| `src/agents/facebook_surfer.py` | Create | DeepAgent implementation |
| `src/main.py` | Create | CLI entry point |
| `tests/test_facebook_surfer.py` | Create | Agent tests |
| `src/tools/base.py` | Modify | Add set_current_page() for tool context |

### Verification

```bash
python -c "
from src.tools.registry import registry, register_all_tools
register_all_tools()
print(f'Registered {len(registry.get_all())} tools')
print(f'Tools: {registry.list_names()}')
"

python -c "
from src.agents.facebook_surfer import FacebookSurferAgent
agent = FacebookSurferAgent()
print(f'Agent created with {len(agent.tools)} tools')
"

python src/main.py --login
python src/main.py "Navigate to facebook.com and take a screenshot"
```

**Expected:** All 23 tools registered (22 + vision), agent executes tasks

**Estimated Effort:** 4-6 hours

---

## Phase 4: LOT Memory

### Objective
Implement ChromaDB-based pattern storage with OpenAI embeddings for semantic recall

### Tasks

- [ ] Create `ChromaStore` wrapper for persistence
- [ ] Implement `save_pattern` tool
- [ ] Implement `recall_patterns` tool with semantic search
- [ ] Add `get_pattern_stats` tool
- [ ] Integrate memory with agent (auto-save, auto-recall)
- [ ] Test memory persistence and learning loop

### Files to Create/Modify

| File | Action | Details |
|------|--------|---------|
| `src/memory/chroma_store.py` | Create | ChromaDB wrapper with OpenAI embeddings (text-embedding-3-small) |
| `src/tools/memory.py` | Create | save, recall, stats tools |
| `src/agents/facebook_surfer.py` | Modify | Add memory integration |

### Verification

```bash
# Requires OPENAI_API_KEY for embeddings
pip install chromadb
python -c "
from src.memory.chroma_store import ChromaStore
store = ChromaStore()
store.add_pattern('Test task', [], 1.0)
results = store.search_patterns('Similar task', n_results=1)
print(f'Found {len(results)} patterns')
"
python -c "
from src.agents.facebook_surfer import FacebookSurferAgent
agent = FacebookSurferAgent(enable_memory=True)
agent.invoke('Get pattern statistics')
"
```

**Expected:** Patterns store/retrieve, semantic search works, agent learns

---

## Phase 5: Integration & Testing

### Objective
End-to-end testing, HITL refinement, Docker containerization, documentation

### Tasks

- [ ] Create E2E test suite (login → post, login → search → comment)
- [ ] Test vision fallback scenarios
- [ ] Test memory learning loop
- [ ] Refine HITL flow with clear prompts
- [ ] Create Dockerfile and docker-compose.yml
- [ ] Write documentation (README, usage, troubleshooting)
- [ ] Add logging, caching, error handling

### Files to Create/Modify

| File | Action | Details |
|------|--------|---------|
| `tests/test_e2e.py` | Create | End-to-end tests with real Facebook |
| `Dockerfile` | Create | Container definition |
| `docker-compose.yml` | Create | Orchestration with volumes |
| `README.md` | Update | Usage instructions, architecture |
| `docs/` | Create | USAGE.md, API.md, TROUBLESHOOTING.md |

### Verification

```bash
pytest tests/test_e2e.py -v -m e2e
docker-compose build
docker-compose up -d
docker-compose exec facebook-surfer python -m src.main --login
docker-compose exec facebook-surfer python -m src.main "Post a hello message"
```

**Expected:** E2E tests pass, Docker works, documentation complete

---

## Summary

### Total Phases: 5
### Total Estimated Effort: 5-9 days

### Key Risks

1. **Facebook anti-bot detection** (HIGH)
   - Mitigation: Reuse TS stealth mode, human-like delays, vision fallback
2. **Python conversion bugs** (MEDIUM)
   - Mitigation: Test tools individually, keep TS reference
3. **Vision + Embeddings API costs** (MEDIUM)
   - Mitigation: Cache results, use selectively. Embeddings: ~$0.02/1M tokens (text-embedding-3-small)
4. **Session persistence** (HIGH)
   - Mitigation: Port proven TS patterns exactly
5. **DeepAgents API changes** (LOW)
   - Mitigation: Pin dependency version

### Dependencies

- **External:** deepagents, langchain, playwright, chromadb, openai
- **Internal:** TypeScript MCP tools (reference only)
- **Sequential:** Phase 1 → 2 → 3 → 4 → 5

### Unresolved Questions

1. Should we use Redis or file-based caching for vision results?
2. What's the optimal pattern retention policy for ChromaDB?
3. Should we implement multi-agent delegation in Phase 6?
4. How to handle Facebook 2FA beyond initial HITL?
5. Production deployment strategy (cloud provider, scaling)?

### Success Criteria

- [ ] Agent navigates Facebook and logs in with HITL
- [ ] Performs basic tasks (post, comment, like) via NL
- [ ] Vision identifies UI elements 90%+ accuracy
- [ ] LOT recalls and reuses patterns
- [ ] Session persists across restarts
- [ ] All 22 tools converted successfully
- [ ] Handles 3+ distinct Facebook task types
- [ ] Vision fallback works when selectors fail
- [ ] Docker deployment works
- [ ] Documentation complete
