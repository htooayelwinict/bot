import { mcpRegistry } from './core/registry';
import { MCPToolDefinition, MCPContext } from './core/types';
import { Page, BrowserContext } from 'playwright';

import { NavigateTool, NavigateBackTool, ScreenshotTool, GetPageInfoTool } from './tools/navigation';
import { ClickTool, TypeTool, SelectOptionTool, HoverTool, PressKeyTool } from './tools/interaction';
import { WaitTool, EvaluateTool, GetSnapshotTool, GetNetworkRequestsTool, GetConsoleMessagesTool } from './tools/utilities';
import { FillFormTool, GetFormDataTool, SubmitFormTool } from './tools/form';
import { TabsTool, ResizeTool, HandleDialogTool, ReloadTool, CloseTool } from './tools/browser';

export class MCPToolsManager {
  private context: MCPContext;
  private initialized = false;

  constructor(private profilePath: string = './profiles/default') {
    this.context = {
      page: null as any,
      context: null as any,
      profile: profilePath
    };
  }

  async initialize(page: Page, context: BrowserContext): Promise<void> {
    this.context.page = page;
    this.context.context = context;

    this.registerAllTools();
    mcpRegistry.setPageContext(page, context);
    this.initialized = true;
  }

  private registerAllTools(): void {
    const page = this.context.page;
    const ctx = this.context.context;

    mcpRegistry.register(new NavigateTool(page, ctx), { category: 'navigation' });
    mcpRegistry.register(new NavigateBackTool(page, ctx), { category: 'navigation' });
    mcpRegistry.register(new ScreenshotTool(page, ctx), { category: 'navigation' });
    mcpRegistry.register(new GetPageInfoTool(page, ctx), { category: 'navigation' });

    mcpRegistry.register(new ClickTool(page, ctx), { category: 'interaction' });
    mcpRegistry.register(new TypeTool(page, ctx), { category: 'interaction' });
    mcpRegistry.register(new SelectOptionTool(page, ctx), { category: 'interaction' });
    mcpRegistry.register(new HoverTool(page, ctx), { category: 'interaction' });
    mcpRegistry.register(new PressKeyTool(page, ctx), { category: 'interaction' });

    mcpRegistry.register(new WaitTool(page, ctx), { category: 'utility' });
    mcpRegistry.register(new EvaluateTool(page, ctx), { category: 'utility' });
    mcpRegistry.register(new GetSnapshotTool(page, ctx), { category: 'utility' });
    mcpRegistry.register(new GetNetworkRequestsTool(page, ctx), { category: 'utility' });
    mcpRegistry.register(new GetConsoleMessagesTool(page, ctx), { category: 'utility' });

    mcpRegistry.register(new FillFormTool(page, ctx), { category: 'form' });
    mcpRegistry.register(new GetFormDataTool(page, ctx), { category: 'form' });
    mcpRegistry.register(new SubmitFormTool(page, ctx), { category: 'form' });

    mcpRegistry.register(new TabsTool(page, ctx), { category: 'browser' });
    mcpRegistry.register(new ResizeTool(page, ctx), { category: 'browser' });
    mcpRegistry.register(new HandleDialogTool(page, ctx), { category: 'browser' });
    mcpRegistry.register(new ReloadTool(page, ctx), { category: 'browser' });
    mcpRegistry.register(new CloseTool(page, ctx), { category: 'browser' });
  }

  async executeTool(name: string, args: any = {}): Promise<any> {
    if (!this.initialized) {
      throw new Error('MCPToolsManager not initialized. Call initialize() first.');
    }

    const tool = mcpRegistry.get(name);
    if (!tool) {
      throw new Error(`Tool not found: ${name}`);
    }

    const result = await tool.execute(args, this.context);

    if (result.isError) {
      throw new Error(result.content[0]?.text || 'Tool execution failed');
    }

    return {
      success: true,
      message: result.content[0]?.text || 'Tool executed successfully',
      data: result._meta || {}
    };
  }

  getToolDefinitions(): MCPToolDefinition[] {
    return mcpRegistry.listDefinitions();
  }

  getToolsByCategory(category: string): MCPToolDefinition[] {
    return mcpRegistry.getByCategory(category).map(tool => tool.definition);
  }

  getToolsByTag(tag: string): MCPToolDefinition[] {
    return mcpRegistry.getByTag(tag).map(tool => tool.definition);
  }

  setToolEnabled(name: string, enabled: boolean): void {
    mcpRegistry.setEnabled(name, enabled);
  }

  getStats(): any {
    return mcpRegistry.getStats();
  }

  isInitialized(): boolean {
    return this.initialized;
  }

  getContext(): MCPContext {
    return this.context;
  }

  updatePageContext(page: Page, context: BrowserContext): void {
    this.context.page = page;
    this.context.context = context;
    mcpRegistry.setPageContext(page, context);
  }
}

export async function createMCPToolsManager(
  page: Page,
  browserContext: BrowserContext,
  profilePath: string = './profiles/default'
): Promise<MCPToolsManager> {
  const manager = new MCPToolsManager(profilePath);
  await manager.initialize(page, browserContext);
  return manager;
}