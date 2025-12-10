# Bot Persona Guide

This guide explains how to create and manage bot personas for different automation tasks.

## What is a Bot Persona?

A bot persona defines the behavioral characteristics and identity of your automation bot:
- Browser fingerprint (user agent, viewport)
- Human-like behavior patterns
- Specific automation workflows
- Isolated profile and session data

## Creating a New Persona

### 1. Define the Persona Profile

Edit `config/bot-config.json`:

```json
{
  "bots": {
    "social-media-bot": {
      "name": "Social Media Manager",
      "description": "Automates social media posting and engagement",
      "headless": false,
      "viewport": { "width": 1366, "height": 768 },
      "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
      "credentials": {
        "username": "social_bot@example.com",
        "password": "secure_password"
      },
      "targetUrls": {
        "login": "https://twitter.com/login",
        "dashboard": "https://twitter.com/home"
      }
    }
  }
}
```

### 2. Create Profile Directory

```bash
mkdir profiles/social-media-bot
```

### 3. Add Docker Service

Edit `docker-compose.yml`:

```yaml
social-media-bot:
  build: .
  container_name: social-media-bot
  volumes:
    - ./profiles/social-media-bot:/app/profiles/social-media-bot
    - ./config:/app/config:ro
  environment:
    - BOT_NAME=social-media-bot
    - PROFILE_PATH=/app/profiles/social-media-bot
  env_file:
    - config/.env
  restart: unless-stopped
```

## Persona Types

### 1. Data Collection Bot
- Purpose: Scrape and collect data
- Characteristics: Fast, efficient, minimal interaction
- Settings: Headless mode, fast timeouts

### 2. Social Media Bot
- Purpose: Post content, engage with users
- Characteristics: Human-like timing, varied interactions
- Settings: Non-headless, random delays, mouse movement

### 3. E-commerce Bot
- Purpose: Monitor prices, make purchases
- Characteristics: Session persistence, cart management
- Settings: Persistent login, cookie management

### 4. Testing Bot
- Purpose: Automated testing
- Characteristics: Repeatable actions, screenshot capture
- Settings: Headless, detailed logging

## Human Behavior Simulation

### Typing Patterns
Configure natural typing delays:

```json
"humanBehavior": {
  "typingDelay": {
    "min": 50,    // Minimum delay between keystrokes (ms)
    "max": 150    // Maximum delay between keystrokes (ms)
  }
}
```

### Random Delays
Add realistic pauses between actions:

```json
"humanBehavior": {
  "randomDelays": {
    "min": 1000,  // Minimum delay between actions (ms)
    "max": 3000   // Maximum delay between actions (ms)
  }
}
```

### Mouse Movement
Enable mouse movement simulation:

```json
"humanBehavior": {
  "mouseMovement": true
}
```

## Profile Isolation

Each persona maintains:
- Separate browser profile directory
- Isolated cookies and sessions
- Unique browser fingerprint
- Independent storage

### Profile Structure
```
profiles/
├── persona1/
│   ├── Default/
│   ├── Cookies/
│   └── profile.json
└── persona2/
    ├── Default/
    ├── Cookies/
    └── profile.json
```

## Best Practices

### 1. Naming Conventions
- Use descriptive names: `social-media-bot`, `price-monitor`
- Avoid special characters
- Keep names consistent across configs

### 2. Security
- Use unique credentials per persona
- Rotate passwords regularly
- Store secrets in environment variables

### 3. Performance
- Use headless mode for non-visual tasks
- Optimize timeouts for target websites
- Monitor resource usage

### 4. Maintenance
- Regularly update user agents
- Clear profiles periodically
- Monitor for detection

## Example Personas

### Reddit Upvote Bot
```json
{
  "reddit-bot": {
    "name": "Reddit Engagement Bot",
    "headless": false,
    "viewport": { "width": 1920, "height": 1080 },
    "humanBehavior": {
      "randomDelays": { "min": 2000, "max": 5000 },
      "mouseMovement": true
    },
    "targetUrls": {
      "login": "https://www.reddit.com/login",
      "home": "https://www.reddit.com"
    }
  }
}
```

### LinkedIn Bot
```json
{
  "linkedin-bot": {
    "name": "LinkedIn Networking Bot",
    "headless": false,
    "viewport": { "width": 1366, "height": 768 },
    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "humanBehavior": {
      "typingDelay": { "min": 100, "max": 200 }
    },
    "targetUrls": {
      "login": "https://www.linkedin.com/login",
      "feed": "https://www.linkedin.com/feed/"
    }
  }
}
```

## Monitoring Personas

Track persona activity:
```bash
# View logs for specific bot
docker-compose logs social-media-bot

# Monitor resource usage
docker stats social-media-bot

# Check profile status
ls -la profiles/social-media-bot/
```

## Scaling Personas

For multiple instances of the same persona:
1. Use numbered suffixes: `bot-1`, `bot-2`
2. Create separate profile directories
3. Configure different credentials
4. Add separate Docker services

## Troubleshooting

### Detection Issues
- Rotate user agents
- Increase human-like delays
- Update browser fingerprints

### Login Problems
- Check credential format
- Verify 2FA requirements
- Clear profile and retry

### Performance Issues
- Reduce screenshot usage
- Optimize timeouts
- Use headless mode when possible