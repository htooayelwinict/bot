# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Setup
npm install                    # Install dependencies
npx playwright install chromium  # Install Playwright browsers
cp config/.env.example config/.env  # Configure environment

# Local Development
npm run login                  # Run human-in-loop login flow
npm run build                  # Compile TypeScript to dist/

# Testing
npm test                       # Run Playwright tests
npm run test:ui                # Run tests with Playwright UI

# Code Quality
npm run lint                   # ESLint check
npm run lint:fix              # Auto-fix linting issues
```

## Architecture Overview

This is a simplified Playwright bot automation system focused on human-in-the-loop login functionality with persistent browser sessions.

### Core Components

1. **Human-in-the-Loop Login (`src/automation/human-in-loop-login.ts`)**
   - Provides interactive login flow for manual authentication
   - Saves browser sessions and cookies for persistence
   - Restores previous sessions to avoid repeated logins
   - Handles Facebook anti-bot detection with realistic browser settings

2. **Bot Framework (`src/bot.ts`)**
   - Basic browser lifecycle management (launch → context → pages)
   - Creates isolated BrowserContext with persistent profiles
   - Configurable user agents, viewports, and timeouts

3. **Profile Management (`src/profile-manager.ts`)**
   - Manages browser profile directories
   - Ensures profile directories exist before use
   - Handles profile cleanup and maintenance

### Key Features

- **Session Persistence**: Saves and restores browser sessions automatically
- **Anti-Detection**: Browser configured to appear human-like to avoid bot detection
- **Retry Logic**: Robust navigation with multiple retry attempts
- **Profile Isolation**: Each login session uses isolated Chrome profile

### Development Workflow

1. **Initial Login**: Run `npm run login` to start interactive login process
2. **Session Saving**: Browser automatically saves session after successful login
3. **Session Restoration**: Subsequent runs automatically restore previous session
4. **Manual Fallback**: If session expires, prompts for manual login again

### File Structure

```
src/
├── run-human-login.ts           # Main entry point
├── bot.ts                       # Basic bot framework
├── profile-manager.ts           # Profile management
└── automation/
    └── human-in-loop-login.ts   # Login implementation
```

### Authentication Flow

1. Attempt to restore saved session
2. Navigate to target site with retry logic
3. If not logged in, open browser for manual login
4. Wait for manual authentication (3-minute timeout)
5. Save new session for future use
6. Take screenshots for verification

### GitHub Context
- [Issue #1: Claude Context 2024-12-11 10:00](https://github.com/htooayelwinict/bot/issues/1)