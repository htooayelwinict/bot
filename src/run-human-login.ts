import { HumanInLoopLogin } from './automation/human-in-loop-login';
import * as fs from 'fs/promises';
import * as path from 'path';

async function runBotWithHumanLogin() {
  console.log('🤖 Bot Starting - Human-in-the-Loop Authentication');
  console.log('=' .repeat(50));

  const profilePath = './profiles/bot-facebook';
  const login = new HumanInLoopLogin();

  // Ensure directories exist
  await fs.mkdir(profilePath, { recursive: true });
  await fs.mkdir('./screenshots', { recursive: true });

  try {
    // Check if we're already logged in
    console.log('1️⃣ Checking login status...');
    let isLoggedIn = false;

    try {
      isLoggedIn = await login.restoreSession(profilePath);
    } catch (e) {
      console.log('   No existing session found');
      isLoggedIn = false;
    }

    if (!isLoggedIn) {
      console.log('\n2️⃣ Not logged in - initiating manual login');
      console.log('   ⚠️  Browser will open - you have 3 minutes to log in\n');

      // Start new login process
      const loginSuccess = await login.startLogin(profilePath);

      if (!loginSuccess) {
        console.log('\n❌ Login failed - bot cannot continue');
        await login.close();
        return;
      }
    } else {
      console.log('\n✅ Already logged in - continuing with automation');
    }

    // At this point, we're logged in - continue with bot tasks
    console.log('\n3️⃣ Login confirmed! Bot can now perform automated tasks...');

    // Take a victory screenshot
    if (login['page']) {
      await login['page'].screenshot({
        path: './screenshots/bot-ready.png',
        fullPage: true
      });
      console.log('📸 Screenshot saved: bot-ready.png');
    }

    // TODO: Add your bot's main automation tasks here
    // Example:
    // await performBotTasks(login['page']);

    console.log('\n✨ Bot session ready for automation!');
    console.log('   Profile saved at:', profilePath);
    console.log('   Next run will automatically restore this session.');

    // Keep browser open for 10 seconds to verify
    console.log('\n⏳ Keeping browser open for 10 seconds for verification...');
    await new Promise(resolve => setTimeout(resolve, 10000));

  } catch (error) {
    console.error('\n💥 Error during bot execution:', error);
  } finally {
    await login.close();
  }
}

// Run the bot
runBotWithHumanLogin().catch(console.error);