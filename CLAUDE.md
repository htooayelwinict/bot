# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

| Command | Purpose |
|--------|---------|
| `npm install` | Install dependencies |
| `npx playwright install chromium` | Install browser |
| `cp config/.env.example config/.env` | Configure environment |
| `npm run login` | Create/restore Facebook session |
| `npm run build` | Compile TypeScript |
| `npm run test:mcp` | Test MCP tools |
| `npm run demo:ai` | Demo AI agent |
| `npm test` | Run Playwright tests |
| `npm run test:ui` | Run tests with Playwright UI |
| `npm run lint` | ESLint check |
| `npm run lint:fix` | Fix ESLint issues automatically |
| `docker-compose up --build` | Build and run containers |
| `docker-compose down` | Stop and remove containers |

## Architecture Overview

Containerized Playwright bot automation with Facebook session management and MCP tools for AI agents.

### Core Components

**Human-in-the-Loop Login** (`src/automation/human-in-loop-login.ts`)
- Facebook authentication with persistent Chrome profiles stored in `./profiles/`
- Anti-bot detection with stealth browser arguments and human-like interaction
- 3-minute manual login fallback with automatic session persistence
- Session validation using `[aria-label*="Account"]` selector
- Automatic cleanup of Chrome lock files (`SingletonLock`, `SingletonSocket`)

**MCP Tools** (`src/mcp-tools/`)
- 22 standardized browser automation tools across 5 categories
- JSON Schema validation with OpenAI function calling compatibility
- Extensible registry pattern with lazy tool instantiation
- Direct Playwright execution without network overhead
- Base tool class with built-in error handling and validation

**Docker Containerization** (`Dockerfile`, `docker-compose.yml`)
- Alpine Linux base with Playwright system dependencies
- Multi-bot support with isolated profiles per container
- Volume mounting for persistent profile storage
- Non-root user execution for security
- Health checks and graceful shutdown support

**Integration Layer** (`src/automation/mcp-playwright-tools.ts`)
- Backward-compatible wrapper maintaining existing API
- Session-aware execution using restored browser contexts
- Automatic initialization of MCP tools with existing sessions

### Development Workflow

1. **Session Setup**: Run `npm run login` if `./profiles/bot-facebook` doesn't exist
2. **Tool Development**: Inherit from `BaseMCPTool`, define JSON Schema, register with `mcpRegistry`
3. **Testing**: Use `npm run test:mcp` to validate tools with Facebook profile
4. **AI Integration**: Use `MCPToolsManager` for orchestration with standardized results

### TypeScript Configuration

- **Target**: ES2020 with CommonJS modules
- **Output**: `./dist/` with declaration and source maps
- **Strict**: Enabled with consistent type checking
- **Playwright**: Type definitions installed via `@playwright/test`

### Testing Strategy

- **Unit Tests**: Use `npm run test:mcp` for MCP tools validation
- **E2E Tests**: Playwright test runner with UI mode (`npm run test:ui`)
- **Demo Scripts**:
  - `src/test-mcp-architecture.ts` - Comprehensive MCP tools testing
  - `src/demo-ai-agent.ts` - AI agent orchestration example

### MCP Tool Categories

- **Navigation** (4): navigate, back, screenshot, page info
- **Interaction** (5): click, type, select, hover, press key
- **Utilities** (5): wait, evaluate, snapshot, network, console
- **Forms** (3): fill, get data, submit
- **Browser** (5): tabs, resize, dialogs, reload, close

### Runtime Behavior

**Session Management**:
- Chrome profiles persisted in `./profiles/bot-facebook/`
- Automatic lock file cleanup on startup
- Account validation using DOM selectors
- Browser context isolation per bot instance

**Tool Execution Pipeline**:
JSON Schema validation → context injection → Playwright execution → result serialization → error handling

**Container Deployment**:
- Each container runs isolated bot with dedicated profile
- Profile volumes mounted for persistence across restarts
- Environment-specific configuration via `.env` files