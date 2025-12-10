import { Page } from 'playwright';

export interface LoginCredentials {
  username: string;
  password: string;
}

export class LoginFlow {
  async login(page: Page, url: string, credentials: LoginCredentials): Promise<boolean> {
    try {
      console.log(`Navigating to ${url}`);
      await page.goto(url, { waitUntil: 'networkidle' });

      // Generic login flow - can be overridden for specific sites
      await this.fillLoginCredentials(page, credentials);
      await this.submitLogin(page);

      // Wait for login to complete
      await page.waitForLoadState('networkidle', { timeout: 10000 });

      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  }

  private async fillLoginCredentials(page: Page, credentials: LoginCredentials): Promise<void> {
    // Try to find username/email input
    const usernameSelectors = [
      'input[name="username"]',
      'input[name="email"]',
      'input[type="email"]',
      'input[id="username"]',
      'input[id="email"]',
      'input[placeholder*="username"]',
      'input[placeholder*="email"]'
    ];

    let usernameInput = null;
    for (const selector of usernameSelectors) {
      try {
        usernameInput = await page.$(selector);
        if (usernameInput) break;
      } catch {
        // Continue to next selector
      }
    }

    if (!usernameInput) {
      throw new Error('Could not find username/email input field');
    }

    await usernameInput.fill(credentials.username);

    // Try to find password input
    const passwordSelectors = [
      'input[name="password"]',
      'input[type="password"]',
      'input[id="password"]',
      'input[placeholder*="password"]'
    ];

    let passwordInput = null;
    for (const selector of passwordSelectors) {
      try {
        passwordInput = await page.$(selector);
        if (passwordInput) break;
      } catch {
        // Continue to next selector
      }
    }

    if (!passwordInput) {
      throw new Error('Could not find password input field');
    }

    await passwordInput.fill(credentials.password);
  }

  private async submitLogin(page: Page): Promise<void> {
    // Try to find submit button
    const submitSelectors = [
      'button[type="submit"]',
      'input[type="submit"]',
      'button:has-text("Login")',
      'button:has-text("Sign in")',
      'button:has-text("Log in")',
      'button:has-text("Continue")',
      '.login-button',
      '.signin-button'
    ];

    for (const selector of submitSelectors) {
      try {
        const button = await page.$(selector);
        if (button) {
          await button.click();
          return;
        }
      } catch {
        // Continue to next selector
      }
    }

    // If no button found, try pressing Enter on password field
    await page.keyboard.press('Enter');
  }

  async isLoggedIn(page: Page): Promise<boolean> {
    // Generic check - look for signs of being logged in
    try {
      // Check if login form is no longer present
      const loginForm = await page.$('form:has(input[type="password"])');
      if (loginForm) {
        return false;
      }

      // Check for common logged-in indicators
      const loggedInIndicators = [
        '[data-testid="user-menu"]',
        '.user-menu',
        '.profile-menu',
        '.logout',
        'button:has-text("Logout")',
        'button:has-text("Sign out")',
        'a:has-text("My Account")'
      ];

      for (const selector of loggedInIndicators) {
        try {
          const element = await page.$(selector);
          if (element) {
            return true;
          }
        } catch {
          // Continue to next selector
        }
      }

      // Check URL for logged-in patterns
      const url = page.url();
      const loggedInPatterns = ['/dashboard', '/profile', '/account', '/home'];

      return loggedInPatterns.some(pattern => url.includes(pattern));
    } catch {
      return false;
    }
  }
}