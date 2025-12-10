import { chromium, BrowserContext, Page } from 'playwright';
import * as fs from 'fs/promises';
import * as path from 'path';

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

    // Launch browser with persistent context and human-like settings
    this.context = await chromium.launchPersistentContext(profilePath, {
      headless: false,
      args: [
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
      ],
      slowMo: 100, // Slightly slow down for human interaction
      viewport: { width: 1920, height: 1080 },
      locale: 'en-US',
      timezoneId: 'America/New_York',
      permissions: ['geolocation', 'notifications'],
      ignoreHTTPSErrors: true
    });

    // Get the first page or create one
    const pages = this.context.pages();
    this.page = pages.length > 0 ? pages[0] : await this.context.newPage();

    // Navigate to Facebook with retry logic
    console.log('📍 Navigating to Facebook...');
    let navigationSuccess = false;
    let attempts = 0;
    const maxAttempts = 3;

    while (!navigationSuccess && attempts < maxAttempts) {
      attempts++;
      try {
        console.log(`   Attempt ${attempts} of ${maxAttempts}...`);
        await this.page.goto('https://www.facebook.com', {
          waitUntil: 'domcontentloaded',
          timeout: 60000
        });

        // Additional wait for page to stabilize
        await this.page.waitForTimeout(2000);

        // Check if page loaded successfully
        const pageTitle = await this.page.title();
        if (pageTitle.includes('Facebook') || pageTitle.includes('Log In')) {
          navigationSuccess = true;
          console.log('✅ Facebook page loaded successfully');
        }
      } catch (error) {
        console.log(`   ⚠️ Navigation attempt ${attempts} failed:`, error instanceof Error ? error.message : 'Unknown error');
        if (attempts < maxAttempts) {
          await this.page.waitForTimeout(3000);
        }
      }
    }

    if (!navigationSuccess) {
      console.log('❌ Failed to navigate to Facebook after', maxAttempts, 'attempts');
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

    // First, check if login page elements are present
    const loginPageSelectors = [
      'input[type="email"]',
      'input[type="password"]',
      'input[name="email"]',
      'input[name="pass"]',
      '[data-testid="royal_email"]'
    ];

    for (const selector of loginPageSelectors) {
      try {
        const element = await this.page.$(selector);
        if (element) {
          // Still on login page
          return false;
        }
      } catch {
        // Continue checking
      }
    }

    // Check for logged-in indicators
    const loggedInSelectors = [
      '[aria-label*="Account"]',
      '[data-testid="bluebar_profile_root"]',
      'a[href*="/me"][role="link"]',
      '[data-visualcompletion="ignore-dynamic"] svg[aria-label="Account"]',
      '[role="complementary"]', // Right column
      '[role="main"]', // Feed
      '[aria-label*="Messenger"]'
    ];

    for (const selector of loggedInSelectors) {
      try {
        const element = await this.page.$(selector);
        if (element) {
          console.log('✅ Detected logged-in state with selector:', selector);
          return true;
        }
      } catch {
        // Continue checking
      }
    }

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

  // Method to use the saved session in future runs
  async restoreSession(profilePath: string): Promise<boolean> {
    console.log('🔄 Attempting to restore saved session...');

    const cookiesFile = path.join(profilePath, 'cookies.json');
    const stateFile = path.join(profilePath, 'state.json');

    try {
      // Check if files exist
      const cookiesExist = await fs.access(cookiesFile).then(() => true).catch(() => false);
      const stateExist = await fs.access(stateFile).then(() => true).catch(() => false);

      if (!cookiesExist && !stateExist) {
        console.log('❌ No saved session found');
        return false;
      }

      // Launch browser with persistent context and human-like settings
      this.context = await chromium.launchPersistentContext(profilePath, {
        headless: false,
        args: [
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
        ],
        viewport: { width: 1920, height: 1080 },
        locale: 'en-US',
        timezoneId: 'America/New_York',
        permissions: ['geolocation', 'notifications'],
        ignoreHTTPSErrors: true
      });

      // If state exists, use it
      if (stateExist) {
        const state = JSON.parse(await fs.readFile(stateFile, 'utf-8'));
        await this.context.addCookies(state.cookies);
        console.log('✅ Session restored from state');
      }

      // Get the first page or create one
    const pages = this.context.pages();
    this.page = pages.length > 0 ? pages[0] : await this.context.newPage();

      // Navigate to Facebook to verify with retry logic
      console.log('📍 Navigating to Facebook to verify session...');
      let navigationSuccess = false;
      let attempts = 0;
      const maxAttempts = 3;

      while (!navigationSuccess && attempts < maxAttempts) {
        attempts++;
        try {
          console.log(`   Verification attempt ${attempts} of ${maxAttempts}...`);
          await this.page.goto('https://www.facebook.com', {
            waitUntil: 'domcontentloaded',
            timeout: 60000
          });

          // Additional wait for page to stabilize
          await this.page.waitForTimeout(2000);
          navigationSuccess = true;
        } catch (error) {
          console.log(`   ⚠️ Navigation attempt ${attempts} failed:`, error instanceof Error ? error.message : 'Unknown error');
          if (attempts < maxAttempts) {
            await this.page.waitForTimeout(3000);
          }
        }
      }

      if (!navigationSuccess) {
        console.log('❌ Failed to navigate to Facebook for verification');
        await this.context?.close();
        this.context = null;
        this.page = null;
        return false;
      }

      // Check if still logged in
      const isLoggedIn = await this.checkIfLoggedIn();

      if (isLoggedIn) {
        console.log('✅ Successfully restored logged-in session');
        // Keep browser open for automation
        return true;
      } else {
        console.log('❌ Session expired - need to log in again');
        // Close the browser and context to clean up
        await this.context?.close();
        this.context = null;
        this.page = null;
        return false;
      }

    } catch (error) {
      console.error('Failed to restore session:', error);
      // Close the browser and context to clean up
      await this.context?.close();
      this.context = null;
      this.page = null;
      return false;
    }
  }
}

// Example usage
async function main() {
  const login = new HumanInLoopLogin();

  // Try to restore existing session first
  const isLoggedIn = await login.restoreSession('./profiles/default');

  if (!isLoggedIn) {
    // If no valid session, start new login process
    const success = await login.startLogin('./profiles/default');

    if (success) {
      console.log('✨ Login process completed successfully!');
    } else {
      console.log('💔 Login process failed');
    }
  }

  // Keep browser open for a bit to see the result
  await new Promise(resolve => setTimeout(resolve, 5000));
  await login.close();
}

// Run if called directly
if (require.main === module) {
  main().catch(console.error);
}