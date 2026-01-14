# Project Overview & PDR

## Project Summary

Facebook Surfer is an AI-powered automation agent that uses DeepAgents + LangChain + Playwright to autonomously interact with Facebook through natural language commands. The agent maintains persistent login sessions, understands Facebook's UI patterns, and can perform complex multi-step workflows like posting content with privacy controls.

## Product Development Requirements (PDR)

### Business Goals

- **Automate Repetitive Tasks**: Reduce manual effort for routine Facebook actions
- **Natural Language Interface**: Control Facebook automation through plain English commands
- **Persistent Sessions**: Maintain login state across runs without repeated authentication
- **Extensible Framework**: Support for additional social platforms via skills system

### User Stories

| ID | As a... | I want to... | So that... |
|----|---------|--------------|------------|
| US-001 | User | Post to Facebook with "Only me" privacy | I can save drafts privately before publishing |
| US-002 | User | Use natural language commands | I don't need to learn scripting or code |
| US-003 | User | Maintain login sessions | I don't have to log in every time |
| US-004 | Developer | Extend with new tools | I can add custom automation workflows |

### Features

| Feature | Status | Priority |
|---------|--------|----------|
| Human-in-the-loop login | Done | High |
| Persistent browser contexts | Done | High |
| Browser tools registry | Done | High |
| DeepAgents integration | Done | High |
| Skills middleware | Done | Medium |
| "Only me" posting workflow | Done | High |
| Privacy selector pattern | Done | High |
| Interactive mode | Done | Medium |
| Debug mode with event streaming | Done | Low |
| ChromaDB long-term memory | Planned | Low |

### Success Metrics

- Login success rate: >95% (3-minute window)
- Task completion rate: >90% for supported workflows
- Session persistence: 24+ hours without re-authentication
- Tool registry: 10+ browser automation tools

## Tech Stack

- **Language**: Python 3.11+
- **Browser Automation**: Playwright (Chromium)
- **Agent Framework**: DeepAgents, LangChain, LangGraph
- **LLM**: OpenRouter API (supports multiple model providers)
- **Validation**: Pydantic
- **CLI**: Click
- **Testing**: Pytest, pytest-asyncio
- **Linting**: Ruff, mypy

## Getting Started

1. **Install dependencies**:
   ```bash
   pip install -e ".[agent,dev]"
   .venv/bin/python -m playwright install chromium
   ```

2. **Configure environment**:
   ```bash
   cp config/.env.example config/.env
   # Edit config/.env with OPENROUTER_API_KEY
   ```

3. **Create Facebook session**:
   ```bash
   .venv/bin/python -m facebook-surfer login
   ```

4. **Run a task**:
   ```bash
   .venv/bin/python -m facebook-surfer run "Post hello world with Only me privacy"
   ```

## Development Phases

- **Phase 1** (Current): Base tools + session management
- **Phase 2**: DeepAgents/LangChain integration ✓ Complete
- **Phase 3**: Enhanced Facebook workflows
- **Phase 4**: ChromaDB long-term memory

## Documentation

- [CLAUDE.md](../CLAUDE.md) - Development commands and critical patterns
- [codebase-summary.md](codebase-summary.md) - File structure and key files
- [code-standards.md](code-standards.md) - Python conventions
- [system-architecture.md](system-architecture.md) - Design and data flow
