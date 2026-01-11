import { MCPTool, MCPToolDefinition } from './types';
import { Page, BrowserContext } from 'playwright';

interface ToolMetadata {
  category?: string;
  tags?: string[];
  enabled?: boolean;
}

interface ToolRegistration {
  tool: MCPTool;
  metadata: ToolMetadata;
}

export class MCPToolRegistry {
  private tools = new Map<string, ToolRegistration>();
  private page?: Page;
  private context?: BrowserContext;

  register(tool: MCPTool, metadata?: ToolMetadata): void {
    this.tools.set(tool.definition.name, {
      tool,
      metadata: { enabled: true, ...metadata }
    });

    if (this.page && this.context && 'setPageContext' in tool) {
      (tool as any).setPageContext(this.page, this.context);
    }
  }

  get(name: string): MCPTool | null {
    const registration = this.tools.get(name);
    return registration?.metadata?.enabled ? registration.tool : null;
  }

  has(name: string): boolean {
    return this.tools.get(name)?.metadata?.enabled === true;
  }

  listDefinitions(): MCPToolDefinition[] {
    const definitions: MCPToolDefinition[] = [];
    for (const registration of this.tools.values()) {
      if (registration.metadata?.enabled) {
        definitions.push(registration.tool.definition);
      }
    }
    return definitions;
  }

  getByCategory(category: string): MCPTool[] {
    return Array.from(this.tools.values())
      .filter(r => r.metadata?.category === category && r.metadata?.enabled)
      .map(r => r.tool);
  }

  getByTag(tag: string): MCPTool[] {
    return Array.from(this.tools.values())
      .filter(r => r.metadata?.tags?.includes(tag) && r.metadata?.enabled)
      .map(r => r.tool);
  }

  setEnabled(name: string, enabled: boolean): void {
    const registration = this.tools.get(name);
    if (registration) {
      registration.metadata = { ...registration.metadata, enabled };
    }
  }

  setPageContext(page: Page, context: BrowserContext): void {
    this.page = page;
    this.context = context;

    for (const registration of this.tools.values()) {
      if ('setPageContext' in registration.tool) {
        (registration.tool as any).setPageContext(page, context);
      }
    }
  }

  clear(): void {
    this.tools.clear();
  }

  getStats(): { total: number; enabled: number; disabled: number; categories: string[]; tags: string[] } {
    let enabled = 0;
    let disabled = 0;
    const categories = new Set<string>();
    const tags = new Set<string>();

    for (const registration of this.tools.values()) {
      if (registration.metadata?.enabled) {
        enabled++;
      } else {
        disabled++;
      }

      if (registration.metadata?.category) {
        categories.add(registration.metadata.category);
      }

      registration.metadata?.tags?.forEach(tag => tags.add(tag));
    }

    return {
      total: this.tools.size,
      enabled,
      disabled,
      categories: Array.from(categories),
      tags: Array.from(tags)
    };
  }
}

export const mcpRegistry = new MCPToolRegistry();