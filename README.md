# Facebook Surfer - AI Automation Agent

Facebook automation agent using DeepAgents + LangChain + Playwright with persistent session management and adaptive learning.

## Quick Start

```bash
# Install dependencies
pip install -e ".[agent,dev]"

# Install Playwright browser
.venv/bin/python -m playwright install chromium

# Configure environment
cp config/.env.example config/.env
# Edit config/.env with OPENROUTER_API_KEY

# Create Facebook session (first time only)
.venv/bin/python -m facebook-surfer login

# Run a task
.venv/bin/python -m facebook-surfer run "Post hello world to Facebook"

# Interactive mode
.venv/bin/python -m facebook-surfer run
```

## Usage Examples

Based on real tasks from the learning database:

### Facebook Posts
```bash
# Create "Only Me" post about a topic
.venv/bin/python -m facebook-surfer run "create an onlyme facebook post about AI"

# Create post with specific content
.venv/bin/python -m facebook-surfer run "create an onlyme facebook post about dogs"
```

### Profile & Content Scraping
```bash
# Extract recent posts from your profile
.venv/bin/python -m facebook-surfer run "go to facebook and my user profile. grab 10 recent posts"

# Scrape posts by specific person
.venv/bin/python -m facebook-surfer run "go to facebook and my user profile. grab 10 recent posts by [Name]"
```

### Messaging
```bash
# Send message to specific person
.venv/bin/python -m facebook-surfer run "send a message to John Doe; message - Hey, how are you?"

# Send greeting to recent contact
.venv/bin/python -m facebook-surfer run "send a greeting message to [Name] in recent message"
```

### Message Analysis
```bash
# Analyze conversation with specific person
.venv/bin/python -m facebook-surfer run "facebook messages; read and analyze the recent convo with [Name]"

# Get important insights from conversations
.venv/bin/python -m facebook-surfer run "facebook messages; analyze and tell me about important things"
```

### News Scraping
```bash
# Scrape latest news from CNN
.venv/bin/python -m facebook-surfer run "go to CNN news and scrape latest breaking news; draft into interesting style snap news"

# Scrape from other news sources
.venv/bin/python -m facebook-surfer run "go to BBC news and scrape breaking news; draft into interesting summary"
```

## Learning & Planning

The agent can learn from past executions to improve future performance:

### Enable Learning

```bash
# Enable trajectory capture and storage
.venv/bin/python -m facebook-surfer run --enable-metrics "Post to group"

# Enable RAG-based planning from historical workflows
.venv/bin/python -m facebook-surfer run --enable-planning "Post to group"

# Full learning loop (plan + store)
.venv/bin/python -m facebook-surfer run --enable-planning --enable-metrics "Post to group"
```

### How It Works

1. **Metrics Collection** (`--enable-metrics`)
   - Captures all tool calls with timing and success/failure
   - Calculates weighted trajectory scores (40/20/20/20)
   - Stores in Qdrant vector database with embeddings

2. **RAG-Based Planning** (`--enable-planning`)
   - Retrieves similar historical workflows via semantic search
   - Generates success plans from proven patterns
   - Injects plans into agent context for better execution

3. **Cold Start**
   - Seed initial trajectories before planning:
   ```bash
   .venv/bin/python scripts/seed_trajectories.py
   ```

### Configuration

Requires `OPENAI_API_KEY` in `config/.env` for embeddings and planning.

For details, see [plan/agent-metrics-rag-learning-20260123-003053/README.md](plan/agent-metrics-rag-learning-20260123-003053/README.md).

## Documentation

| Doc | Description |
|-----|-------------|
| [CLAUDE.md](CLAUDE.md) | Development commands and architecture |
| [docs/project-overview-pdr.md](docs/project-overview-pdr.md) | Project goals, features, and PDR |
| [docs/codebase-summary.md](docs/codebase-summary.md) | File structure and key files |
| [docs/code-standards.md](docs/code-standards.md) | Python conventions and patterns |
| [docs/system-architecture.md](docs/system-architecture.md) | Design and data flow |

## Tech Stack

- **Backend:** Python 3.11+, Playwright
- **Agent Framework:** DeepAgents, LangChain, LangGraph
- **Vector Database:** Qdrant (local persistent storage)
- **Embeddings:** OpenAI `text-embedding-3-small`
- **Testing:** Pytest, pytest-asyncio
- **Linting:** Ruff, mypy

## Commands

| Command | Purpose |
|---------|---------|
| `.venv/bin/pip install -e ".[agent]"` | Install with agent dependencies |
| `.venv/bin/python -m facebook-surfer login` | Create Facebook session |
| `.venv/bin/python -m facebook-surfer run "task"` | Run single task |
| `.venv/bin/python -m facebook-surfer run --stream` | Stream mode |
| `.venv/bin/python -m facebook-surfer run --debug` | Debug mode |
| `.venv/bin/python -m facebook-surfer run --enable-metrics "task"` | Enable trajectory storage |
| `.venv/bin/python -m facebook-surfer run --enable-planning "task"` | Enable RAG-based planning |
| `.venv/bin/python scripts/seed_trajectories.py` | Seed initial trajectories |
| `.venv/bin/python -m pytest tests/` | Run tests |

## Project Structure

- `src/session/` - Facebook session management with HITL login
- `src/tools/` - Browser automation tools with registry pattern
  - `security.py` - Prompt injection defense for untrusted browser content
- `src/agents/` - Agent implementations with shared utilities
  - `facebook_surfer.py` - Main execution agent
  - `planner.py` - RAG-based workflow planning
  - `reflection.py` - Trajectory analysis for pattern learning
  - `utils.py` - Shared utilities (OpenRouter config, JSON parsing)
- `src/metrics/` - Trajectory capture, scoring, and PII redaction
- `src/storage/` - Qdrant vector database for semantic retrieval
- `skills/` - Domain-specific guidance for workflows
- `scripts/` - Utility scripts (trajectory seeding)
- `profiles/` - Persistent browser contexts (gitignored)
- `qdrant_db/` - Local vector database storage (gitignored)

## License

MIT
