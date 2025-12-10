import { Bot } from '../src/bot';
import { ProfileManager } from '../src/profile-manager';
import { CookieManager } from '../src/automation/cookie-manager';
import * as path from 'path';

async function runBotWithExistingCookies() {
  const botName = 'bot-with-cookies';
  const profilePath = `./profiles/${botName}`;

  // Initialize profile and bot
  const profileManager = new ProfileManager(profilePath);
  await profileManager.ensureProfileExists();

  const bot = new Bot(botName, profileManager, { headless: false });
  await bot.start();

  // Get the browser context
  const page = await bot.newPage();
  const context = page.context();

  // Initialize cookie manager
  const cookieManager = new CookieManager(profilePath);

  // Method 1: Import from cookies.txt file
  const cookiesFile = path.join(__dirname, 'cookies.txt');
  try {
    await cookieManager.importCookiesTxt(cookiesFile, context);
    console.log('Successfully imported cookies from cookies.txt');
  } catch (error) {
    console.log('No cookies.txt file found, proceeding without imported cookies');
  }

  // Now navigate to the site - you should be logged in
  await page.goto('https://example.com/dashboard');

  // Check if logged in
  const isLoggedIn = await page.$('a[href*="logout"]');
  if (isLoggedIn) {
    console.log('Successfully logged in with imported cookies!');

    // Take a screenshot to verify
    await page.screenshot({
      path: `./screenshots/cookie-login-${Date.now()}.png`,
      fullPage: true
    });
  } else {
    console.log('Not logged in - cookies may be expired');
  }

  // Method 2: Export current cookies for future use
  const exportPath = path.join(profilePath, 'current-cookies.txt');
  await cookieManager.exportCookies(context, exportPath);

  await page.close();
  await bot.stop();
}

// Chrome profile path examples for different OS:
/*
Mac: ~/Library/Application Support/Google/Chrome
Windows: %LOCALAPPDATA%\Google\Chrome\User Data
Linux: ~/.config/google-chrome
*/

// Alternative: Direct Chrome profile import
async function importFromChromeProfile() {
  const chromeProfilePath = '/Users/YOUR_USERNAME/Library/Application Support/Google/Chrome';
  const targetDomain = 'example.com';

  const profileManager = new ProfileManager('./profiles/imported-bot');
  await profileManager.ensureProfileExists();

  const bot = new Bot('imported-bot', profileManager);
  await bot.start();

  const page = await bot.newPage();
  const context = page.context();
  const cookieManager = new CookieManager('./profiles/imported-bot');

  // This would require sqlite3 package to read Chrome's SQLite database
  // await cookieManager.importFromChromeProfile(chromeProfilePath, targetDomain, context);

  console.log('Chrome profile import requires sqlite3 implementation');

  await page.close();
  await bot.stop();
}

// Run the example
runBotWithExistingCookies().catch(console.error);