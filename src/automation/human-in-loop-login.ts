import { chromium, BrowserContext, Page } from 'playwright';
import * as fs from 'fs/promises';
import * as path from 'path';

const BROWSER_ARGS = [
  '--no-sandbox',
  '--disable-setuid-sandbox',
  '--disable-blink-features=AutomationControlled',
  '--disable-web-security',
  '--disable-features=VizDisplayCompositor',
  '--disable-extensions-file-access-check',
  '--disable-extensions-http-throttling',
  '--disable-ipc-flooding-protection',
  '--disable-backgrounding-occluded-windows',
  '--disable-renderer-backgrounding',
  '--disable-dev-shm-usage',
  '--no-first-run',
  '--no-default-browser-check'
] as const;

const LOGIN_SELECTORS = [
  'input[type="email"]',
  'input[type="password"]',
  'input[name="email"]',
  'input[name="pass"]',
  '[data-testid="royal_email"]'
] as const;

const LOGGED_IN_SELECTORS = [
  '[aria-label*="Account"]',
  '[data-testid="bluebar_profile_root"]',
  'a[href*="/me"][role="link"]',
  '[data-visualcompletion="ignore-dynamic"] svg[aria-label="Account"]',
  '[role="complementary"]',
  '[role="main"]',
  '[aria-label*="Messenger"]'
] as const;

export class HumanInLoopLogin {
  private context: BrowserContext | null = null;
  private page: Page | null = null;

  async startLogin(profilePath: string = './profiles/default'): Promise<boolean> {
    console.log('🚀 Starting human-in-the-loop login process...');
    console.log('⏱️  You have 3 minutes to log in manually');

    // Clean up any existing lock files
    try {
      await fs.unlink(path.join(profilePath, 'SingletonLock'));
      await fs.unlink(path.join(profilePath, 'SingletonSocket'));
    } catch {
      // Ignore errors if files don't exist
    }

    this.context = await chromium.launchPersistentContext(profilePath, {
      headless: false,
      args: [...BROWSER_ARGS],
      slowMo: 100,
      viewport: { width: 1920, height: 1080 },
      locale: 'en-US',
      timezoneId: 'America/New_York',
      permissions: ['geolocation', 'notifications'],
      ignoreHTTPSErrors: true
    });

    // Get the first page or create one
    const pages = this.context.pages();
    this.page = pages.length > 0 ? pages[0] : await this.context.newPage();

    if (!await this.navigateToFacebook()) {
      return false;
    }

    // Wait for manual login with timeout
    const loginSuccess = await this.waitForManualLogin();

    if (loginSuccess) {
      console.log('✅ Login successful! Saving session...');
      await this.saveSession(profilePath);
      return true;
    } else {
      console.log('❌ Login timeout or failed');
      return false;
    }
  }

  private async waitForManualLogin(): Promise<boolean> {
    if (!this.page) return false;

    const maxWaitTime = 180000; // 3 minutes in milliseconds
    const checkInterval = 2000; // Check every 2 seconds
    let elapsed = 0;

    console.log('⏳ Waiting for you to log in...');
    console.log('   Browser window is open - please log in manually');

    while (elapsed < maxWaitTime) {
      // Check if we're still on login page
      const isLoggedIn = await this.checkIfLoggedIn();

      if (isLoggedIn) {
        return true;
      }

      // Show progress
      const remainingSeconds = Math.floor((maxWaitTime - elapsed) / 1000);
      if (elapsed % 10000 === 0) { // Every 10 seconds
        console.log(`   ⏰ Time remaining: ${remainingSeconds}s`);
      }

      await this.page.waitForTimeout(checkInterval);
      elapsed += checkInterval;
    }

    return false;
  }

  private async checkIfLoggedIn(): Promise<boolean> {
    if (!this.page) return false;

    for (const selector of LOGIN_SELECTORS) {
      try {
        if (await this.page.$(selector)) {
          return false;
        }
      } catch {
        continue;
      }
    }

    for (const selector of LOGGED_IN_SELECTORS) {
      try {
        if (await this.page.$(selector)) {
          console.log('✅ Detected logged-in state with selector:', selector);
          return true;
        }
      } catch {
        continue;
      }
    }

    return false;
  }

  private async navigateToFacebook(): Promise<boolean> {
    if (!this.page) return false;

    console.log('📍 Navigating to Facebook...');
    const maxAttempts = 3;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        console.log(`   Attempt ${attempt} of ${maxAttempts}...`);
        await this.page.goto('https://www.facebook.com', {
          waitUntil: 'domcontentloaded',
          timeout: 60000
        });

        await this.page.waitForTimeout(2000);

        const pageTitle = await this.page.title();
        if (pageTitle.includes('Facebook') || pageTitle.includes('Log In')) {
          console.log('✅ Facebook page loaded successfully');
          return true;
        }
      } catch (error) {
        console.log(`   ⚠️ Navigation attempt ${attempt} failed:`, error instanceof Error ? error.message : 'Unknown error');
        if (attempt < maxAttempts) {
          await this.page.waitForTimeout(3000);
        }
      }
    }

    console.log('❌ Failed to navigate to Facebook after', maxAttempts, 'attempts');
    return false;
  }

  private async saveSession(profilePath: string): Promise<void> {
    if (!this.context) return;

    try {
      // Ensure profile directory exists
      await fs.mkdir(profilePath, { recursive: true });

      // Get cookies and save them
      const cookies = await this.context.cookies();
      const cookiesFile = path.join(profilePath, 'cookies.json');

      await fs.writeFile(cookiesFile, JSON.stringify(cookies, null, 2));
      console.log(`💾 Session saved to ${cookiesFile}`);
      console.log(`   Saved ${cookies.length} cookies`);

      // Save state as well
      const stateFile = path.join(profilePath, 'state.json');
      const state = await this.context.storageState();
      await fs.writeFile(stateFile, JSON.stringify(state, null, 2));
      console.log(`💾 Browser state saved to ${stateFile}`);

    } catch (error) {
      console.error('Failed to save session:', error);
    }
  }

  async close(): Promise<void> {
    if (this.page) {
      await this.page.screenshot({
        path: './screenshots/final-state.png',
        fullPage: true
      });
    }

    if (this.context) {
      await this.context.close();
    }

    console.log('🔚 Browser closed');
  }

  // Expose current page and context for integration
  getPage(): Page | null {
    return this.page;
  }

  getContext(): BrowserContext | null {
    return this.context;
  }

  async restoreSession(profilePath: string): Promise<boolean> {
    console.log('🔄 Attempting to restore saved session...');

    const cookiesFile = path.join(profilePath, 'cookies.json');
    const stateFile = path.join(profilePath, 'state.json');

    try {
      const cookiesExist = await fs.access(cookiesFile).then(() => true).catch(() => false);
      const stateExist = await fs.access(stateFile).then(() => true).catch(() => false);

      if (!cookiesExist && !stateExist) {
        console.log('❌ No saved session found');
        return false;
      }

      this.context = await chromium.launchPersistentContext(profilePath, {
        headless: false,
        args: [...BROWSER_ARGS],
        viewport: { width: 1920, height: 1080 },
        locale: 'en-US',
        timezoneId: 'America/New_York',
        permissions: ['geolocation', 'notifications'],
        ignoreHTTPSErrors: true
      });

      if (stateExist) {
        const state = JSON.parse(await fs.readFile(stateFile, 'utf-8'));
        await this.context.addCookies(state.cookies);
        console.log('✅ Session restored from state');
      }

      const pages = this.context.pages();
      this.page = pages.length > 0 ? pages[0] : await this.context.newPage();

      if (!await this.navigateToFacebook()) {
        await this.context?.close();
        this.context = null;
        this.page = null;
        return false;
      }

      const isLoggedIn = await this.checkIfLoggedIn();

      if (isLoggedIn) {
        console.log('✅ Successfully restored logged-in session');
        return true;
      } else {
        console.log('❌ Session expired - need to log in again');
        await this.context?.close();
        this.context = null;
        this.page = null;
        return false;
      }

    } catch (error) {
      console.error('Failed to restore session:', error);
      await this.context?.close();
      this.context = null;
      this.page = null;
      return false;
    }
  }
}