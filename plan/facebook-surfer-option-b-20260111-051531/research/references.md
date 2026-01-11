# References & External Documentation

**Last Updated:** 2026-01-11

---

## Core Dependencies

### DeepAgents (LangChain)
- **Overview:** https://docs.langchain.com/oss/python/deepagents/overview
- **Quickstart:** https://docs.langchain.com/oss/python/deepagents/quickstart
- **API Reference:** https://python.langchain.com/docs/reference/deepagents/
- **Key Concepts:**
  - `create_deep_agent()` - Main factory function
  - Built-in tools: `write_todos`, `ls`, `read_file`, `write_file`, `task`
  - Memory: LangGraph Store for persistence
  - Planning: Automatic task breakdown

### LangChain
- **Python Docs:** https://python.langchain.com
- **Tools:** https://python.langchain.com/docs/concepts/tools
- **Pydantic Tools:** https://python.langchain.com/docs/how_to/custom_tools/
- **Key Pattern:**
  ```python
  from pydantic import BaseModel, Field
  from langchain.tools import tool

  class ToolArgs(BaseModel):
      arg: str = Field(description="...")

  @tool
  def my_tool(args: ToolArgs) -> str:
      """Tool description for LLM."""
      return "result"
  ```

### LangGraph
- **Store (Memory):** https://langchain-ai.github.io/langgraph/concepts/persistence/#memory-store
- **Checkpointing:** https://langchain-ai.github.io/langgraph/concepts/persistence/
- **Key Pattern:**
  ```python
  from langgraph.store.memory import InMemoryStore
  from langgraph.checkpoint.memory import MemoryCheckpointSaver

  store = InMemoryStore()
  checkpointer = MemoryCheckpointSaver()
  ```

### OpenAI Vision
- **API Docs:** https://platform.openai.com/docs/guides/vision
- **Python SDK:** https://github.com/openai/openai-python
- **GPT-4o Usage:**
  ```python
  from openai import OpenAI

  client = OpenAI()
  response = client.chat.completions.create(
      model="gpt-4o",
      messages=[{
          "role": "user",
          "content": [
              {"type": "text", "text": "Describe this image"},
              {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
          ]
      }
      ]
  )
  ```

### OpenAI Embeddings
- **API Docs:** https://platform.openai.com/docs/guides/embeddings
- **text-embedding-3-small:** ~$0.02/1M tokens, best value for semantic search
- **ChromaDB Integration:**
  ```python
  from chromadb.utils import embedding_functions

  openai_ef = embedding_functions.OpenAIEmbeddingFunction(
      api_key=os.getenv("OPENAI_API_KEY"),
      model_name="text-embedding-3-small"
  )

  collection = client.get_or_create_collection(
      name="patterns",
      embedding_function=openai_ef
  )
  ```

### Playwright Python
- **Docs:** https://playwright.dev/python/
- **API Reference:** https://playwright.dev/python/docs/api/class-playwright
- **Key Methods:**
  - `launch_persistent_context()` - Session persistence
  - `page.goto()` - Navigation
  - `page.locator()` - Element selection
  - `page.screenshot()` - Screenshots
  - `page.evaluate()` - JavaScript execution

### ChromaDB
- **Docs:** https://docs.trychroma.com/
- **Python Quickstart:** https://docs.trychroma.com/getting-started/quickstart
- **LangChain Integration:** https://python.langchain.com/docs/integrations/vectorstores/chroma/

## Best Practices

### Tool Schema Design
1. **Clear Descriptions:** LLM uses these to decide when to call tools
2. **Type Validation:** Use Pydantic for strict checking
3. **Default Values:** Reduce cognitive load on LLM
4. **Enum Constraints:** Guide LLM to valid inputs

### Memory Hygiene
1. **Summarize:** Don't store raw conversation logs
2. **Embeddings:** Use semantic search for retrieval
3. **Scoring:** Rate patterns by success rate
4. **Pruning:** Remove low-quality patterns

### Vision Optimization
1. **Cache Results:** Same screenshot = cached analysis
2. **Selective Use:** Only when selectors fail
3. **Compression:** Resize screenshots < 1MB
4. **Prompt Engineering:** Be specific about what to find

### Anti-Detection
1. **Human-like Delays:** Random 100-500ms between actions
2. **Mouse Movement:** Use `hover()` before clicks
3. **Viewport:** Standard desktop size (1920x1080)
4. **User Agent:** Don't override default

## Architecture Patterns

### Tool Categories
1. **Navigation** (4 tools): navigate, back, screenshot, page_info
2. **Interaction** (5 tools): click, type, select, hover, press_key
3. **Forms** (3 tools): fill, get_data, submit
4. **Utilities** (5 tools): wait, evaluate, snapshot, network, console
5. **Browser** (5 tools): tabs, resize, dialog, reload, close

### Vision Fallback Strategy
```python
# 1. Try CSS selector first
try:
    element = page.locator(selector).first
    element.click()
except:
    # 2. Fall back to vision
    screenshot = page.screenshot()
    analysis = vision_analyze_ui(screenshot, "Find the login button")
    # 3. Use vision result to locate element
    element = page.locator(analysis.selector).first
    element.click()
```

### LOT Memory Pattern
```python
# Store successful pattern
def save_pattern(task: str, actions: List[Action]):
    pattern = {
        "task": task,
        "actions": [a.dict() for a in actions],
        "success_rate": 1.0,
        "timestamp": datetime.now().isoformat()
    }
    store.put(("patterns",), task, pattern)

# Recall similar patterns
def recall_patterns(task: str) -> List[Pattern]:
    items = store.search(("patterns",), query=task, limit=3)
    return [item.value for item in items]
```

## Troubleshooting

### Common Issues

1. **Facebook Session Expired**
   - Symptom: Login check fails
   - Fix: Re-run HITL login flow

2. **Vision API Timeout**
   - Symptom: > 30s response
   - Fix: Resize screenshot, add timeout

3. **Selector Not Found**
   - Symptom: Playwright timeout
   - Fix: Use vision fallback

4. **ChromaDB Persistence**
   - Symptom: Memory lost on restart
   - Fix: Use persistent directory (`./memory/`)

5. **DeepAgent Planning Loop**
   - Symptom: Infinite recursion
   - Fix: Add step limit, validate plan

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Tool Execution | < 2s | Average per tool |
| Vision Analysis | < 5s | GPT-4o response |
| Session Restore | < 5s | Profile load time |
| Pattern Recall | < 1s | Vector similarity |
| Agent Planning | < 10s | For 10-step tasks |

## Security Considerations

1. **Credentials:** Never hardcode, use `.env`
2. **Session Data:** Encrypt cookies.json
3. **Memory Storage:** Sanitize before storing
4. **Screenshots:** Blur sensitive information
5. **API Keys:** Rotate regularly, monitor usage

## Testing Strategy

### Unit Tests
- Each tool in isolation
- Mock Playwright page
- Validate Pydantic schemas

### Integration Tests
- Session management
- Tool orchestration
- Vision + selector fallback

### E2E Tests
- Real Facebook login
- Multi-step tasks
- Memory persistence

### Test Cases
1. Login → Post to timeline
2. Login → Comment on post
3. Login → Search for user
4. Login → Like post
5. Session persistence
6. Vision fallback
7. Pattern recall
