# Getting Started with Playwright Bot Automation

This guide will help you set up and run your Playwright automation bots with containerized user profiles.

## Prerequisites

- Node.js 18 or higher
- Docker and Docker Compose
- Git

## Installation

1. **Clone and setup the repository**:
```bash
cd /path/to/your/bot/directory
npm install
```

2. **Install Playwright browsers**:
```bash
npx playwright install chromium
```

3. **Configure your bot**:
```bash
cp config/.env.example config/.env
# Edit config/.env with your credentials
```

## Running Locally

### Development Mode
```bash
npm run dev
```

### Production Mode
```bash
npm run build
npm start
```

## Running with Docker

### Single Bot
```bash
docker-compose up bot1
```

### Multiple Bots
```bash
docker-compose up
```

### Build and Run
```bash
docker-compose up --build
```

## Configuration

### Environment Variables
Key variables in `config/.env`:
- `BOT_NAME`: Unique identifier for your bot
- `HEADLESS`: Run browser in headless mode (true/false)
- `TARGET_URL`: URL to automate
- `TARGET_USERNAME`: Login username
- `TARGET_PASSWORD`: Login password

### Bot Configuration
Detailed settings in `config/bot-config.json`:
- Browser settings (viewport, timeout)
- User credentials
- Target URLs
- Human behavior simulation

## Profile Management

Each bot maintains a persistent browser profile in the `profiles/` directory:
- `profiles/bot1/`: Profile for bot1
- `profiles/bot2/`: Profile for bot2

Profiles contain:
- Login sessions
- Cookies
- Local storage
- Browser settings

## Creating a New Bot

1. **Add to docker-compose.yml**:
```yaml
newbot:
  build: .
  volumes:
    - ./profiles/newbot:/app/profiles/newbot
    - ./config:/app/config:ro
  environment:
    - BOT_NAME=newbot
    - PROFILE_PATH=/app/profiles/newbot
  env_file:
    - config/.env
```

2. **Update config/bot-config.json**:
```json
{
  "bots": {
    "newbot": {
      "name": "New Bot",
      "credentials": {
        "username": "your_username",
        "password": "your_password"
      }
    }
  }
}
```

3. **Run the new bot**:
```bash
docker-compose up newbot
```

## Custom Automation

Create custom automation scripts in `src/automation/`:

```typescript
import { Bot } from '../bot';
import { Page } from 'playwright';

async function customAutomation(bot: Bot) {
  const page = await bot.newPage();

  // Your automation logic here
  await page.goto('https://example.com');
  // ... perform actions

  await page.close();
}
```

## Troubleshooting

### Browser Not Starting
- Ensure Playwright browsers are installed: `npx playwright install`
- Check Docker logs: `docker-compose logs bot1`

### Login Issues
- Verify credentials in `config/.env`
- Check target URLs in `config/bot-config.json`
- Enable screenshots for debugging

### Profile Issues
- Clear profile: Delete the profile directory
- Check permissions on profiles folder
- Verify Docker volume mounts

### Common Solutions
- Restart containers: `docker-compose down && docker-compose up`
- Rebuild images: `docker-compose up --build`
- Check logs: `docker-compose logs`

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use environment variables** for sensitive data
3. **Rotate passwords** regularly
4. **Limit profile permissions**
5. **Monitor bot activity** with logging

## Next Steps

- Explore the automation examples in `src/automation/`
- Customize page objects for your target websites
- Set up CI/CD for automated deployments
- Implement monitoring and alerting