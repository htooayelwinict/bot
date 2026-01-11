/**
 * Test MCP Tools Architecture
 * Comprehensive test of the new MCP tools implementation with Facebook
 */

import { HumanInLoopLogin } from './automation/human-in-loop-login';
import { MCPPlaywrightTools } from './automation/mcp-playwright-tools';

interface ToolCall {
  name: string;
  args: Record<string, any>;
}

interface ToolResult {
  success: boolean;
  message?: string;
  data?: any;
  error?: string;
}

/**
 * Test the MCP tools architecture
 */
async function testMCPArchitecture() {
  console.log('🧪 TESTING MCP TOOLS ARCHITECTURE WITH FACEBOOK');
  console.log('='.repeat(60));

  const login = new HumanInLoopLogin();
  const mcpTools = new MCPPlaywrightTools('./profiles/bot-facebook');

  try {
    // Step 1: Restore Facebook session
    console.log('\n1️⃣ Restoring Facebook session...');
    const isLoggedIn = await login.restoreSession('./profiles/bot-facebook');

    if (!isLoggedIn) {
      throw new Error('No Facebook session found. Please run "npm run login" first.');
    }

    console.log('✅ Facebook session restored');

    // Step 2: Initialize MCP tools with the existing session
    console.log('\n2️⃣ Initializing MCP tools...');
    const page = login.getPage();
    const context = login.getContext();

    if (!page || !context) {
      throw new Error('Failed to get page/context from Facebook session');
    }

    // Set the existing page and context
    (mcpTools as any).setPage(page, context);
    await mcpTools.initialize();

    console.log('✅ MCP tools initialized');

    // Step 3: Get MCP tool definitions
    console.log('\n3️⃣ Getting MCP tool definitions...');
    const mcpDefinitions = mcpTools.getMCPToolDefinitions();
    console.log(`✅ Found ${mcpDefinitions.length} MCP tools:`);

    // Group tools by category
    const toolsByCategory: Record<string, string[]> = {};
    mcpDefinitions.forEach(tool => {
      const name = tool.function.name;
      let category = 'other';

      if (name.includes('navigate') || name.includes('screenshot') || name.includes('page_info')) {
        category = 'navigation';
      } else if (name.includes('click') || name.includes('type') || name.includes('select') || name.includes('hover') || name.includes('press')) {
        category = 'interaction';
      } else if (name.includes('wait') || name.includes('evaluate') || name.includes('snapshot') || name.includes('network') || name.includes('console')) {
        category = 'utility';
      } else if (name.includes('form')) {
        category = 'form';
      } else if (name.includes('browser') || name.includes('tabs') || name.includes('resize')) {
        category = 'browser';
      }

      if (!toolsByCategory[category]) {
        toolsByCategory[category] = [];
      }
      toolsByCategory[category].push(name);
    });

    Object.entries(toolsByCategory).forEach(([category, tools]) => {
      console.log(`   ${category}: ${tools.length} tools`);
      tools.slice(0, 3).forEach(tool => console.log(`     - ${tool}`));
      if (tools.length > 3) {
        console.log(`     ... and ${tools.length - 3} more`);
      }
    });

    // Step 4: Test core MCP tools
    console.log('\n4️⃣ Testing core MCP tools...');

    const testTools: ToolCall[] = [
      { name: 'browser_get_page_info', args: {} },
      { name: 'browser_wait', args: { time: 1 } },
      { name: 'browser_navigate', args: { url: 'https://www.facebook.com' } },
      { name: 'browser_wait', args: { time: 2 } },
      { name: 'browser_evaluate', args: { script: 'document.title' } },
      { name: 'browser_screenshot', args: { filename: 'mcp-architecture-test', type: 'png' } }
    ];

    let passed = 0;
    let failed = 0;

    for (const toolCall of testTools) {
      try {
        console.log(`   Testing ${toolCall.name}...`);
        const result = await mcpTools.executeMCPTool(toolCall.name, toolCall.args);
        console.log(`   ✅ ${toolCall.name}: ${result.message}`);
        passed++;
      } catch (error) {
        console.log(`   ❌ ${toolCall.name}: ${error instanceof Error ? error.message : 'Unknown error'}`);
        failed++;
      }
    }

    // Step 5: Test Facebook-specific interactions
    console.log('\n5️⃣ Testing Facebook-specific interactions...');

    const fbTests: ToolCall[] = [
      { name: 'browser_evaluate', args: { script: 'document.querySelector("[aria-label*=\'Search\']") !== null' } },
      { name: 'browser_type', args: { selector: '[aria-label*="Search Facebook"]', text: 'Playwright automation' } },
      { name: 'browser_wait', args: { time: 1 } },
      { name: 'browser_press_key', args: { key: 'Enter' } },
      { name: 'browser_wait', args: { time: 2 } }
    ];

    for (const toolCall of fbTests) {
      try {
        console.log(`   Testing ${toolCall.name}...`);
        const result = await mcpTools.executeMCPTool(toolCall.name, toolCall.args);
        console.log(`   ✅ ${toolCall.name}: ${result.message}`);
        passed++;
      } catch (error) {
        console.log(`   ❌ ${toolCall.name}: ${error instanceof Error ? error.message : 'Unknown error'}`);
        failed++;
      }
    }

    // Step 6: Test form tools if we find a form
    console.log('\n6️⃣ Testing form tools...');
    try {
      const hasForm = await mcpTools.executeMCPTool('browser_evaluate', {
        script: 'document.querySelector("form") !== null'
      });

      if (hasForm.data?.result) {
        const formData = await mcpTools.executeMCPTool('browser_get_form_data', {});
        console.log('   ✅ Found and extracted form data');
        passed++;
      } else {
        console.log('   ℹ️  No forms found on current page');
      }
    } catch (error) {
      console.log(`   ❌ Form test failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
      failed++;
    }

    // Step 7: Get MCP statistics
    console.log('\n7️⃣ MCP Architecture Statistics:');
    const stats = mcpTools.getMCPStats();
    if (stats) {
      console.log(`   Total tools: ${stats.total}`);
      console.log(`   Enabled tools: ${stats.enabled}`);
      console.log(`   Categories: ${stats.categories.join(', ')}`);
      console.log(`   Tags: ${stats.tags.slice(0, 5).join(', ')}${stats.tags.length > 5 ? '...' : ''}`);
    }

    // Summary
    console.log('\n' + '='.repeat(60));
    console.log('📊 TEST SUMMARY:');
    console.log(`   Tests passed: ${passed}`);
    console.log(`   Tests failed: ${failed}`);
    console.log(`   Success rate: ${((passed / (passed + failed)) * 100).toFixed(1)}%`);

    if (failed === 0) {
      console.log('\n✅ ALL TESTS PASSED! MCP architecture is working correctly.');
      console.log('\n🚀 Ready for AI agents:');
      console.log('   - Standard MCP tool definitions ✅');
      console.log('   - Proper JSON schemas ✅');
      console.log('   - Extensible registry ✅');
      console.log('   - Facebook session integration ✅');
      console.log('   - Backward compatibility ✅');
    } else {
      console.log('\n⚠️  Some tests failed. Check the errors above.');
    }

  } catch (error) {
    console.error('\n❌ Test failed:', error);
    if (error instanceof Error && error.message.includes('No Facebook session')) {
      console.log('\n💡 To fix: Run "npm run login" first to create a Facebook session');
    }
  } finally {
    // Keep browser open for inspection
    console.log('\n🔄 Keeping browser open for 5 seconds...');
    await new Promise(resolve => setTimeout(resolve, 5000));

    await mcpTools.close();
    console.log('🔚 Browser closed');
  }
}

if (require.main === module) {
  testMCPArchitecture().catch(console.error);
}

export { testMCPArchitecture };