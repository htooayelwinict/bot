/**
 * Demo: How an AI agent would use the MCP tools
 * Shows standardized tool execution with OpenAI function calling format
 */

import { HumanInLoopLogin } from './automation/human-in-loop-login';
import { MCPPlaywrightTools } from './automation/mcp-playwright-tools';

interface ToolCall {
  name: string;
  arguments: Record<string, any>;
}

interface ToolResult {
  success: boolean;
  message: string;
  data?: any;
}

/**
 * Simulated AI Agent that uses MCP tools
 */
class AIAgent {
  private tools: MCPPlaywrightTools;
  private availableTools: any[] = [];

  constructor(tools: MCPPlaywrightTools) {
    this.tools = tools;
  }

  async initialize(): Promise<void> {
    await this.tools.initialize();
    this.availableTools = this.tools.getMCPToolDefinitions();
    console.log(`🤖 AI Agent initialized with ${this.availableTools.length} tools`);
  }

  /**
   * Simulate AI planning and execution
   */
  async executeTask(taskDescription: string): Promise<void> {
    console.log(`\n📋 Task: ${taskDescription}`);
    console.log('─'.repeat(50));

    // Simulate AI reasoning and planning
    const plan = this.createPlan(taskDescription);

    console.log('\n🧠 AI Plan:');
    plan.forEach((step, i) => {
      console.log(`   ${i + 1}. ${step.name}(${JSON.stringify(step.arguments)})`);
    });

    // Execute the plan
    console.log('\n🔧 Executing plan:');
    for (const step of plan) {
      try {
        const result = await this.executeTool(step);
        const status = result.success ? '✅' : '❌';
        console.log(`   ${status} ${step.name}: ${result.message}`);

        if (result.data && Object.keys(result.data).length > 0) {
          console.log(`      Data: ${JSON.stringify(result.data)}`);
        }
      } catch (error) {
        console.log(`   ❌ ${step.name}: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    }

    console.log('\n✅ Task completed!');
  }

  /**
   * Create a plan based on the task (simplified AI reasoning)
   */
  private createPlan(task: string): ToolCall[] {
    const plans: Record<string, ToolCall[]> = {
      'Check Facebook notifications': [
        { name: 'browser_get_page_info', arguments: {} },
        { name: 'browser_screenshot', arguments: { filename: 'facebook-notifications' } }
      ],
      'Search for Playwright on Facebook': [
        { name: 'browser_navigate', arguments: { url: 'https://www.facebook.com' } },
        { name: 'browser_wait', arguments: { time: 2 } },
        { name: 'browser_type', arguments: { selector: '[aria-label*="Search Facebook"]', text: 'Playwright automation testing' } },
        { name: 'browser_press_key', arguments: { key: 'Enter' } },
        { name: 'browser_wait', arguments: { time: 3 } },
        { name: 'browser_screenshot', arguments: { filename: 'playwright-search-results' } }
      ],
      'Extract page information': [
        { name: 'browser_get_page_info', arguments: {} },
        { name: 'browser_evaluate', arguments: { script: 'document.title' } },
        { name: 'browser_evaluate', arguments: { script: 'Array.from(document.querySelectorAll("a")).map(a => a.href).slice(0, 10)' } }
      ],
      'Test form interaction': [
        { name: 'browser_navigate', arguments: { url: 'https://httpbin.org/forms/post' } },
        { name: 'browser_wait', arguments: { time: 2 } },
        { name: 'browser_fill_form', arguments: {
          fields: [
            { name: 'custname', type: 'textbox', value: 'AI Agent Test' },
            { name: 'custtel', type: 'textbox', value: '555-1234' },
            { name: 'custemail', type: 'textbox', value: 'ai@example.com' }
          ]
        }},
        { name: 'browser_screenshot', arguments: { filename: 'form-filled' } },
        { name: 'browser_submit_form', arguments: {} },
        { name: 'browser_wait', arguments: { time: 2 } }
      ]
    };

    return plans[task] || [{ name: 'browser_get_page_info', arguments: {} }];
  }

  /**
   * Execute a single tool call
   */
  async executeTool(toolCall: ToolCall): Promise<ToolResult> {
    try {
      const result = await this.tools.executeMCPTool(toolCall.name, toolCall.arguments);
      return {
        success: true,
        message: result.message || 'Tool executed successfully',
        data: result.data
      };
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Get available tools (for AI to see what it can do)
   */
  getAvailableTools(): any[] {
    return this.availableTools;
  }
}

/**
 * Run the AI agent demo
 */
async function runAIDemo() {
  console.log('🤖 AI AGENT DEMO: USING MCP TOOLS');
  console.log('='.repeat(60));

  const login = new HumanInLoopLogin();
  const mcpTools = new MCPPlaywrightTools('./profiles/bot-facebook');
  const agent = new AIAgent(mcpTools);

  try {
    // Restore Facebook session
    console.log('\n1️⃣ Restoring Facebook session...');
    const isLoggedIn = await login.restoreSession('./profiles/bot-facebook');

    if (!isLoggedIn) {
      throw new Error('No Facebook session found. Please run "npm run login" first.');
    }

    console.log('✅ Facebook session restored');

    // Get page and context
    const page = login.getPage();
    const context = login.getContext();

    if (!page || !context) {
      throw new Error('Failed to get page/context from Facebook session');
    }

    // Set up MCP tools with existing session
    (mcpTools as any).setPage(page, context);
    await agent.initialize();

    // Show available tools
    console.log('\n2️⃣ Available tools for AI:');
    const tools = agent.getAvailableTools();
    console.log(`   Total: ${tools.length} tools`);

    // Show some examples
    console.log('\n   Example tools:');
    tools.slice(0, 5).forEach(tool => {
      console.log(`   - ${tool.function.name}: ${tool.function.description}`);
    });
    console.log('   ... and more');

    // Execute different tasks
    console.log('\n3️⃣ Executing AI tasks...');

    await agent.executeTask('Extract page information');
    await agent.executeTask('Check Facebook notifications');
    await agent.executeTask('Search for Playwright on Facebook');

    // Show final state
    console.log('\n4️⃣ Final page state:');
    const pageInfo = await agent.executeTool({ name: 'browser_get_page_info', arguments: {} });
    if (pageInfo.success) {
      console.log(`   URL: ${pageInfo.data.url}`);
      console.log(`   Title: ${pageInfo.data.title}`);
    }

    console.log('\n✅ Demo completed successfully!');
    console.log('\n📈 What we demonstrated:');
    console.log('   1. AI agents can use standardized MCP tools ✅');
    console.log('   2. Tools follow OpenAI function calling format ✅');
    console.log('   3. Session persistence with Facebook ✅');
    console.log('   4. Multi-step task execution ✅');
    console.log('   5. Error handling and validation ✅');
    console.log('   6. Extensible tool registry ✅');

  } catch (error) {
    console.error('\n❌ Demo failed:', error);
    if (error instanceof Error && error.message.includes('No Facebook session')) {
      console.log('\n💡 To fix: Run "npm run login" first to create a Facebook session');
    }
  } finally {
    // Keep browser open for a bit
    console.log('\n🔄 Keeping browser open for 5 seconds...');
    await new Promise(resolve => setTimeout(resolve, 5000));

    await mcpTools.close();
    console.log('\n🔚 Browser closed');
  }
}

if (require.main === module) {
  runAIDemo().catch(console.error);
}

export { runAIDemo, AIAgent };