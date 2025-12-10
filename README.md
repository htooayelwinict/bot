# Playwright Bot Automation

Containerized bot automation using Playwright with persistent user profiles.

## Overview

This project enables running automated bots with isolated browser profiles that maintain login sessions and state across container restarts.

## Features

- **Containerized Playwright** - Isolated browser automation in Docker
- **Persistent Profiles** - User profiles mounted as volumes for session persistence
- **Multi-Bot Support** - Run multiple isolated bots simultaneously
- **TypeScript** - Type-safe automation scripts
- **Page Objects** - Maintainable automation patterns

## Quick Start

1. Install dependencies:
```bash
npm install
```

2. Install Playwright browsers:
```bash
npx playwright install
```

3. Build and run with Docker:
```bash
docker-compose up --build
```

## Project Structure

- `src/` - TypeScript source code
- `profiles/` - Persistent user profile data
- `config/` - Configuration files
- `infra/` - Docker and deployment configurations
- `docs/` - Documentation

## Configuration

Copy `config/.env.example` to `config/.env` and configure your bot settings.

## License

MIT