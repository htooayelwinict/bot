# Existing Code Patterns

**Analyzed:** TypeScript MCP tools and session management

---

## Session Management Pattern

### File: `src/automation/human-in-loop-login.ts`

**Key Patterns to Port:**

```typescript
// 1. Browser Args (Stealth Mode)
const BROWSER_ARGS = [
  '--no-sandbox',
  '--disable-setuid-sandbox',
  '--disable-blink-features=AutomationControlled',
  '--disable-web-security',
  // ... more args
];

// 2. Login Detection
const LOGGED_IN_SELECTORS = [
  '[aria-label*="Account"]',
  '[data-testid="bluebar_profile_root"]',
  'a[href*="/me"][role="link"]'
];

// 3. Lock File Cleanup
await fs.unlink(path.join(profilePath, 'SingletonLock'));
await fs.unlink(path.join(profilePath, 'SingletonSocket'));

// 4. Persistent Context
this.context = await chromium.launchPersistentContext(profilePath, {
  headless: false,
  args: BROWSER_ARGS,
  slowMo: 100,
  viewport: { width: 1920, height: 1080 },
  locale: 'en-US',
  timezoneId: 'America/New_York'
});

// 5. Polling Login State
while (elapsed < maxWaitTime) {
  if (await this.checkIfLoggedIn()) return true;
  await this.page.waitForTimeout(checkInterval);
  elapsed += checkInterval;
}
```

**Python Conversion Pattern:**
```python
# Playwright Python equivalent
from playwright.sync_api import sync_playwright

BROWSER_ARGS = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-blink-features=AutomationControlled',
]

LOGGED_IN_SELECTORS = [
    '[aria-label*="Account"]',
    '[data-testid="bluebar_profile_root"]',
]

class PlaywrightSession:
    def __init__(self, profile_path: str):
        self.profile_path = profile_path
        self.context = None
        self.page = None

    def start_login(self) -> bool:
        # Clean lock files
        for lock_file in ['SingletonLock', 'SingletonSocket']:
            try:
                os.remove(os.path.join(self.profile_path, lock_file))
            except FileNotFoundError:
                pass

        # Launch persistent context
        with sync_playwright() as p:
            self.context = p.chromium.launch_persistent_context(
                self.profile_path,
                headless=False,
                args=BROWSER_ARGS,
                slow_mo=100,
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
                timezone_id='America/New_York'
            )

            # Poll for login
            return self._wait_for_login()
```

## MCP Tool Pattern

### File: `src/mcp-tools/tools/navigation.ts`

**TypeScript Tool Structure:**
```typescript
export class NavigateTool extends BaseMCPTool {
  definition = {
    name: 'browser_navigate',
    description: 'Navigate to a specific URL...',
    inputSchema: {
      type: 'object',
      properties: {
        url: { type: 'string', description: '...' },
        waitUntil: { type: 'string', enum: [...], default: 'load' }
      },
      required: ['url']
    },
    metadata: { tags: ['navigation'], rateLimit: 10 }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { url, waitUntil = 'load' } = args;
    const { page } = context;
    await page.goto(url, { waitUntil });
    return {
      content: [{ type: 'text', text: `Navigated to ${url}` }]
    };
  }
}
```

**Python LangChain Conversion:**
```python
from pydantic import BaseModel, Field
from langchain.tools import tool

class NavigateArgs(BaseModel):
    url: str = Field(description="The URL to navigate to")
    wait_until: str = Field(
        default="load",
        description="When to consider navigation successful",
        enum=["load", "domcontentloaded", "networkidle"]
    )

@tool
def browser_navigate(args: NavigateArgs, page: Page) -> str:
    """Navigate to a specific URL. Waits for the page to load before returning."""
    page.goto(args.url, wait_until=args.wait_until, timeout=30000)
    return f"Navigated to {args.url}\nPage title: {page.title()}\nFinal URL: {page.url}"
```

## Agent Orchestration Pattern

### File: `src/demo-ai-agent.ts`

**Agent Structure:**
```typescript
class AIAgent {
  private tools: MCPPlaywrightTools;

  async executeTask(taskDescription: string): Promise<void> {
    // 1. Create plan
    const plan = this.createPlan(taskDescription);

    // 2. Execute tools in sequence
    for (const step of plan) {
      const result = await this.executeTool(step);
      // Handle result
    }
  }

  async executeTool(toolCall: ToolCall): Promise<ToolResult> {
    const result = await this.tools.executeMCPTool(
      toolCall.name,
      toolCall.arguments
    );
    return { success: true, message: result.message };
  }
}
```

**Python DeepAgent Pattern:**
```python
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

# Create agent
agent = create_deep_agent(
    model="gpt-4o",
    tools=[browser_navigate, browser_click, vision_analyze_ui],
    store=chroma_store,
    checkpointer=checkpointer,
    system_prompt="You are a Facebook user simulator..."
)

# Execute task
result = agent.invoke({
    "messages": [("user", "Post a hello message on my timeline")]
})
```

## Registry Pattern

### File: `src/mcp-tools/core/registry.ts`

**TypeScript Registry:**
```typescript
export class MCPToolRegistry {
  private tools = new Map<string, ToolRegistration>();

  register(tool: MCPTool, metadata?: ToolMetadata): void {
    this.tools.set(tool.definition.name, {
      tool,
      metadata: { enabled: true, ...metadata }
    });
  }

  get(name: string): MCPTool | null {
    const registration = this.tools.get(name);
    return registration?.metadata?.enabled ? registration.tool : null;
  }

  listDefinitions(): MCPToolDefinition[] {
    return Array.from(this.tools.values())
      .filter(r => r.metadata?.enabled)
      .map(r => r.tool.definition);
  }
}
```

**Python Pattern (Simpler):**
```python
# LangChain tools are self-registering via decorator
from langchain.tools import tool

@tool
def browser_navigate(args: NavigateArgs) -> str:
    """Navigate to a specific URL."""
    # Implementation

# Collect all tools
tools = [
    browser_navigate,
    browser_click,
    browser_type,
    # ... all tools
]

# DeepAgent auto-discovers tool schemas
agent = create_deep_agent(tools=tools)
```

## Form Handling Pattern

### File: `src/mcp-tools/tools/form.ts`

**Key Pattern - Field Resolution:**
```typescript
private async resolveFieldLocator(
  page: Page,
  identifiers: Array<string | undefined>,
  timeout: number,
  fallbackLocators: Array<() => Locator> = []
): Promise<Locator> {
  const locatorFactories: Array<() => Locator> = [];

  // Try multiple strategies
  for (const identifier of identifiers) {
    locatorFactories.push(
      () => page.getByLabel(identifier).first(),
      () => page.getByPlaceholder(identifier).first()
    );
  }

  locatorFactories.push(...fallbackLocators);

  // Try each until timeout
  for (const factory of locatorFactories) {
    try {
      const locator = factory();
      await locator.waitFor({ timeout });
      return locator;
    } catch {
      continue;
    }
  }

  throw new Error(`Unable to locate field`);
}
```

**Python Conversion:**
```python
def _resolve_field_locator(
    self,
    page: Page,
    identifiers: List[str],
    timeout: int = 5000,
    fallback_selectors: List[str] = []
) -> Locator:
    """Try multiple strategies to locate a form field."""
    strategies = []

    for identifier in identifiers:
        strategies.extend([
            page.get_by_label(identifier, exact=True).first,
            page.get_by_placeholder(identifier, exact=True).first,
            page.locator(f'[name="{identifier}"]').first,
        ])

    for strategy in strategies:
        try:
            locator = strategy()
            locator.wait_for(state="visible", timeout=timeout)
            return locator
        except:
            continue

    raise Exception(f"Unable to locate field: {identifiers}")
```

## Error Handling Pattern

### TypeScript:
```typescript
protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
  try {
    // Implementation
    return { content: [{ type: 'text', text: 'Success' }] };
  } catch (error) {
    return this.errorResult(`Failed: ${error.message}`);
  }
}
```

### Python:
```python
@tool
def browser_navigate(args: NavigateArgs) -> str:
    """Navigate to a specific URL."""
    try:
        page.goto(args.url, wait_until=args.wait_until)
        return f"Navigated to {args.url}"
    except Exception as e:
        return f"Navigation failed: {str(e)}"
```

## Files to Reference During Implementation

1. **Session Management:** `src/automation/human-in-loop-login.ts`
   - Browser launch arguments
   - Login detection logic
   - Session persistence

2. **Tools:** All files in `src/mcp-tools/tools/`
   - Input schemas (convert to Pydantic)
   - Execution logic (port to Python)
   - Error handling

3. **Agent:** `src/demo-ai-agent.ts`
   - Task execution flow
   - Tool orchestration
   - Result handling

4. **Registry:** `src/mcp-tools/core/registry.ts`
   - Tool registration (simplify for Python)
   - Metadata handling
