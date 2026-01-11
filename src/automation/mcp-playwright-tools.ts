import { MCPToolsManager } from '../mcp-tools/mcp-tools-manager';
import { Page, BrowserContext } from 'playwright';

export class MCPPlaywrightTools {
  private mcpManager: MCPToolsManager | null = null;
  private page: Page | null = null;
  private context: BrowserContext | null = null;

  constructor(public profilePath: string = './profiles/default') {}

  setPage(page: Page, context: BrowserContext): void {
    this.page = page;
    this.context = context;
  }

  getPage(): Page | null {
    return this.page;
  }

  getContext(): BrowserContext | null {
    return this.context;
  }

  async initialize(): Promise<void> {
    if (!this.page || !this.context) {
      throw new Error('Page and context must be set via setPage() before initializing');
    }

    this.mcpManager = new MCPToolsManager(this.profilePath);
    await this.mcpManager.initialize(this.page, this.context);
  }

  async executeMCPTool(name: string, args: any = {}): Promise<any> {
    if (!this.mcpManager) {
      throw new Error('MCP Manager not initialized. Call initialize() first.');
    }

    return this.mcpManager.executeTool(name, args);
  }

  getMCPToolDefinitions(): any[] {
    if (!this.mcpManager) {
      throw new Error('MCP Manager not initialized. Call initialize() first.');
    }

    return this.mcpManager.getToolDefinitions().map(def => ({
      type: 'function',
      function: {
        name: def.name,
        description: def.description,
        parameters: def.inputSchema
      }
    }));
  }

  getMCPStats(): any {
    return this.mcpManager?.getStats() || null;
  }

  setMCPToolEnabled(name: string, enabled: boolean): void {
    this.mcpManager?.setToolEnabled(name, enabled);
  }

  async close(): Promise<void> {
    if (this.context) {
      await this.context.close();
    }
    this.page = null;
    this.context = null;
    this.mcpManager = null;
  }
}
