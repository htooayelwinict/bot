import { chromium, Browser, BrowserContext, Page } from 'playwright';
import { ProfileManager } from './profile-manager';

export interface BotConfig {
  headless?: boolean;
  userAgent?: string;
  viewport?: { width: number; height: number };
  timeout?: number;
}

export class Bot {
  private name: string;
  private profileManager: ProfileManager;
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private config: BotConfig;

  constructor(name: string, profileManager: ProfileManager, config: BotConfig = {}) {
    this.name = name;
    this.profileManager = profileManager;
    this.config = {
      headless: process.env.NODE_ENV === 'production' || (config.headless ?? false),
      userAgent: config.userAgent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      viewport: config.viewport || { width: 1920, height: 1080 },
      timeout: config.timeout || 30000
    };
  }

  async start(): Promise<void> {
    console.log(`Starting bot ${this.name} with browser context`);

    try {
      // Launch browser with Chromium
      this.browser = await chromium.launch({
        headless: this.config.headless,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-gpu',
          '--disable-features=VizDisplayCompositor'
        ]
      });

      // Create context with persistent profile
      this.context = await this.browser.newContext({
        userAgent: this.config.userAgent,
        viewport: this.config.viewport,
        ignoreHTTPSErrors: true,
        // Use the mounted profile path
        ...(!this.config.headless && {
          userDataDir: this.profileManager.getProfilePath()
        })
      });

      // Add authentication for non-headless mode
      if (!this.config.headless) {
        const username = process.env.BROWSER_USERNAME;
        const password = process.env.BROWSER_PASSWORD;

        if (username && password) {
          console.log('Setting up browser authentication');
          await this.context.route('**/*', (route) => {
            const headers = route.request().headers();
            headers['Authorization'] = `Basic ${Buffer.from(`${username}:${password}`).toString('base64')}`;
            route.continue({ headers });
          });
        }
      }

      console.log(`Bot ${this.name} started successfully`);
      console.log(`Headless mode: ${this.config.headless}`);
      console.log(`Profile path: ${this.profileManager.getProfilePath()}`);

    } catch (error) {
      console.error(`Failed to start bot ${this.name}:`, error);
      throw error;
    }
  }

  async stop(): Promise<void> {
    console.log(`Stopping bot ${this.name}`);

    try {
      if (this.context) {
        await this.context.close();
        this.context = null;
      }

      if (this.browser) {
        await this.browser.close();
        this.browser = null;
      }

      console.log(`Bot ${this.name} stopped successfully`);
    } catch (error) {
      console.error(`Error stopping bot ${this.name}:`, error);
    }
  }

  async newPage(): Promise<Page> {
    if (!this.context) {
      throw new Error(`Bot ${this.name} is not started. Call start() first.`);
    }

    const page = await this.context.newPage();

    // Set default timeout
    page.setDefaultTimeout(this.config.timeout!);

    // Add console logging
    page.on('console', (msg) => {
      console.log(`[${this.name}] Page console:`, msg.text());
    });

    // Add error logging
    page.on('pageerror', (err) => {
      console.error(`[${this.name}] Page error:`, err.message);
    });

    return page;
  }

  getBotName(): string {
    return this.name;
  }

  isRunning(): boolean {
    return this.browser !== null && this.context !== null;
  }
}