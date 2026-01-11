# Phase 5: Integration & Testing

**Objective:** End-to-end testing, HITL refinement, Docker containerization, documentation

---

## Prerequisites

- Phase 1-3b complete
- Phase 4 (LOT Memory) complete
- Agent fully functional with memory
- All tools tested individually

---

## Tasks

### 5.1 End-to-End Testing

- [ ] Create E2E test suite
- [ ] Test real Facebook workflows
- [ ] Test vision fallback scenarios
- [ ] Test memory learning loop
- [ ] Test error recovery

**Files:**
- `tests/test_e2e.py`

**Test Scenarios:**
```python
import pytest
from src.session.playwright_session import PlaywrightSession
from src.agents.facebook_surfer import FacebookSurferAgent

@pytest.mark.e2e
def test_login_and_post():
    """Test complete login and post workflow."""
    # Setup
    session = PlaywrightSession()

    # Login
    assert session.start_login()

    # Create agent
    from src.tools.base import set_current_page
    set_current_page(session.get_page())

    agent = FacebookSurferAgent()

    # Execute task
    result = agent.invoke(
        "Post 'Hello from Facebook Surfer Agent!' on my timeline"
    )

    # Verify
    assert result["success"] is True
    assert "posted" in str(result).lower()

    session.close()

@pytest.mark.e2e
def test_login_search_comment():
    """Test login, search, and comment workflow."""
    session = PlaywrightSession()
    assert session.start_login()

    from src.tools.base import set_current_page
    set_current_page(session.get_page())

    agent = FacebookSurferAgent()

    # Search
    result = agent.invoke(
        "Search for 'Playwright automation' on Facebook"
    )
    assert result["success"] is True

    # Comment on first result
    result = agent.invoke(
        "Comment 'Great content!' on the first post"
    )
    assert result["success"] is True

    session.close()

@pytest.mark.e2e
def test_vision_fallback():
    """Test vision fallback when selectors fail."""
    session = PlaywrightSession()
    assert session.restore_session()

    from src.tools.base import set_current_page
    set_current_page(session.get_page())

    # Use tool with vision fallback
    from src.tools.vision import click_with_vision_fallback

    result = click_with_vision_fallback(
        selector=".invalid-selector-xyz-123",
        task_context="Click the menu button"
    )

    # Should succeed via vision
    assert "clicked" in result.lower() or "vision" in result.lower()

    session.close()

@pytest.mark.e2e
def test_memory_learning():
    """Test agent learns from patterns."""
    session = PlaywrightSession()
    assert session.start_login()

    from src.tools.base import set_current_page
    set_current_page(session.get_page())

    agent = FacebookSurferAgent(enable_memory=True)

    # First execution (should save pattern)
    result1 = agent.invoke_with_learning(
        "Navigate to facebook.com"
    )
    assert result1["success"] is True

    # Check pattern was saved
    from src.tools.memory import get_pattern_stats, GetPatternStatsArgs
    stats = get_pattern_stats.func(GetPatternStatsArgs())
    assert "Total Patterns: 1" in stats

    # Second execution (should recall pattern)
    result2 = agent.invoke_with_learning(
        "Go to facebook.com"
    )
    assert result2["success"] is True

    session.close()
```

### 5.2 HITL Refinement

- [ ] Refine HITL prompts
- [ ] Add approval confirmation
- [ ] Implement pause/resume flow
- [ ] Add session state persistence

**Files to Modify:**
- `src/session/playwright_session.py`
- `src/agents/facebook_surfer.py`

**HITL Flow:**
```python
class FacebookSurferAgent:
    def invoke_with_hitl(self, task: str, thread_id: str = "default") -> dict:
        """Execute task with human-in-the-loop for sensitive actions."""
        config = {"configurable": {"thread_id": thread_id}}

        # Check if login needed
        from src.session.playwright_session import PlaywrightSession
        session = PlaywrightSession()

        if not session.restore_session():
            print("\n" + "="*60)
            print("HUMAN-IN-THE-LOOP: LOGIN REQUIRED")
            print("="*60)
            print("A browser window will open. Please log in manually.")
            print("You have 3 minutes. The agent will wait for confirmation.\n")

            # Start login
            success = session.start_login()

            if not success:
                return {
                    "success": False,
                    "error": "Login failed or timed out"
                }

            print("\nLogin confirmed! Resuming task execution...\n")

        # Set page context
        from src.tools.base import set_current_page
        set_current_page(session.get_page())

        # Execute task
        try:
            result = self.agent.invoke(
                {"messages": [("user", task)]},
                config=config
            )
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            session.close()
```

### 5.3 Docker Containerization

- [ ] Create Dockerfile
- [ ] Create docker-compose.yml
- [ ] Add health checks
- [ ] Configure volume mounts

**Files:**
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright browsers
RUN npx -y playwright install --with-deps chromium

# Set working directory
WORKDIR /app

# Copy requirements
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application
COPY src/ src/
COPY config/ config/

# Create directories
RUN mkdir -p profiles memory screenshots

# Set environment
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.session.playwright_session import PlaywrightSession; s=PlaywrightSession(); s.restore_session() and s.close()" || exit 1

# Run application
CMD ["python", "-m", "src.main"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  facebook-surfer:
    build: .
    container_name: facebook-surfer-agent
    volumes:
      - ./profiles:/app/profiles
      - ./memory:/app/memory
      - ./screenshots:/app/screenshots
      - ./config:/app/config
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - FACEBOOK_EMAIL=${FACEBOOK_EMAIL}
      - FACEBOOK_PASSWORD=${FACEBOOK_PASSWORD}
      - HEADLESS=${HEADLESS:-false}
    env_file:
      - config/.env
    ports:
      - "8000:8000"  # For potential web interface
    restart: unless-stopped
    stdin_open: true
    tty: true
```

### 5.4 Documentation

- [ ] Update README.md
- [ ] Create usage guide
- [ ] Add API documentation
- [ ] Create troubleshooting guide

**Files:**
- `README.md` (update)
- `docs/USAGE.md`
- `docs/API.md`
- `docs/TROUBLESHOOTING.md`

**README.md:**
```markdown
# Facebook Surfer Agent

Autonomous Facebook automation agent using LangChain DeepAgents and GPT-4o vision.

## Features

- 22 browser automation tools converted from TypeScript to Python
- GPT-4o vision for UI understanding when selectors fail
- LOT (Learning Over Time) via ChromaDB
- HITL (Human-in-the-Loop) for Facebook login
- Docker containerization

## Quick Start

### Installation

\`\`\`bash
# Clone repo
git clone <repo>
cd bot

# Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Install Playwright browser
playwright install chromium

# Configure environment
cp config/.env.example config/.env
# Edit config/.env with your credentials
\`\`\`

### Usage

\`\`\`bash
# Login (first time only)
python -m src.main --login

# Execute task
python -m src.main "Post a hello message on my timeline"

# Interactive mode
python -m src.main
\`\`\`

### Docker

\`\`\`bash
# Build and run
docker-compose up --build

# Login
docker-compose exec facebook-surfer python -m src.main --login

# Execute task
docker-compose exec facebook-surfer python -m src.main "Search for Playwright"
\`\`\`

## Architecture

\`\`\`
src/
├── agents/
│   └── facebook_surfer.py    # DeepAgent implementation
├── tools/
│   ├── navigation.py          # Navigate, back, screenshot, page_info
│   ├── interaction.py         # Click, type, hover, select, press_key
│   ├── forms.py               # Fill, get_data, submit
│   ├── utilities.py           # Wait, evaluate, snapshot, network, console
│   ├── browser.py             # Tabs, resize, dialog, reload, close
│   ├── vision.py              # GPT-4o vision tool
│   └── memory.py              # LOT memory tools
├── session/
│   └── playwright_session.py  # Session management
└── main.py                    # CLI entry point
\`\`\`

## Testing

\`\`\`bash
# Unit tests
pytest tests/ -v

# E2E tests (requires Facebook session)
pytest tests/test_e2e.py -v -m e2e

# Coverage
pytest --cov=src tests/
\`\`\`

## License

MIT
```

### 5.5 Performance Optimization

- [ ] Add caching for vision results
- [ ] Optimize screenshot compression
- [ ] Add rate limiting for API calls
- [ ] Implement connection pooling

**Files:**
- `src/utils/cache.py`
- `src/utils/limits.py`

**Caching:**
```python
from functools import lru_cache
import hashlib

def cache_key(screenshot_path: str, task: str) -> str:
    """Generate cache key for vision results."""
    with open(screenshot_path, "rb") as f:
        image_hash = hashlib.md5(f.read()).hexdigest()
    return f"{image_hash}:{task}"

@lru_cache(maxsize=100)
def get_cached_vision_result(key: str) -> str | None:
    """Get cached vision result if available."""
    # Check Redis or file-based cache
    pass

def cache_vision_result(key: str, result: str):
    """Cache vision result."""
    # Store in Redis or file
    pass
```

### 5.6 Error Handling & Logging

- [ ] Add structured logging
- [ ] Implement retry logic
- [ ] Add error recovery
- [ ] Create debug mode

**Files:**
- `src/utils/logging.py`
- `src/utils/retries.py`

**Logging:**
```python
import logging
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `tests/test_e2e.py` | End-to-end tests |
| `Dockerfile` | Container definition |
| `docker-compose.yml` | Orchestration |
| `.dockerignore` | Docker exclusions |
| `docs/USAGE.md` | Usage guide |
| `docs/API.md` | API documentation |
| `docs/TROUBLESHOOTING.md` | Troubleshooting |
| `src/utils/cache.py` | Caching utilities |
| `src/utils/logging.py` | Logging configuration |

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/session/playwright_session.py` | Refine HITL flow |
| `src/agents/facebook_surfer.py` | Add error handling |
| `README.md` | Update with new information |

---

## Verification

```bash
# 1. Run E2E tests
pytest tests/test_e2e.py -v -m e2e

# 2. Test HITL flow
python -m src.main --login
# Complete login in browser window
python -m src.main "Post a test message"

# 3. Test memory persistence
python -m src.main "Navigate to facebook.com"
# Check memory was saved
python -c "from src.tools.memory import get_pattern_stats; print(get_pattern_stats())"
# Restart and verify recall

# 4. Build Docker image
docker-compose build

# 5. Run in Docker
docker-compose up -d
docker-compose exec facebook-surfer python -m src.main --login
docker-compose exec facebook-surfer python -m src.main "Get page info"

# 6. Test health check
docker-compose ps
curl http://localhost:8000/health

# 7. Test performance
time python -m src.main "Navigate to facebook.com"
time python -m src.main "Take a screenshot"

# 8. Check logs
tail -f logs/facebook-surfer.log

# 9. Memory cleanup
rm -rf ./memory/*  # Clear LOT memory
rm -rf ./screenshots/*  # Clear screenshots

# 10. Full cleanup
docker-compose down -v
```

**Expected Results:**
- E2E tests pass with real Facebook
- HITL login completes successfully
- Agent posts/comments/searches
- Memory patterns save and recall
- Docker container builds/runs
- Health checks pass
- Performance acceptable (< 10s for simple tasks)

---

## Estimated Effort

**1-2 days**

- E2E testing: 4 hours
- HITL refinement: 2 hours
- Docker setup: 2 hours
- Documentation: 2 hours
- Optimization: 2 hours

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Facebook blocks automated account | Use stealth mode, human-like delays |
| E2E tests flaky | Add retries, use wait conditions |
| Docker image too large | Use Alpine base, multi-stage builds |
| Memory leaks | Limit cache size, cleanup resources |

---

## Dependencies

- Phase 1-3b: Foundation + Vision + Tool Conversion + Agent Assembly (required)
- Phase 4: LOT Memory (required)

---

## Exit Criteria

- [ ] E2E tests pass for 3+ workflows
- [ ] HITL login smooth and reliable
- [ ] Docker container builds/runs
- [ ] Documentation complete
- [ ] Performance acceptable
- [ ] Memory persists correctly
- [ ] Error handling robust
- [ ] Logging works
- [ ] Health checks pass
- [ ] **MVP COMPLETE**

---

## Success Metrics (Overall Project)

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
