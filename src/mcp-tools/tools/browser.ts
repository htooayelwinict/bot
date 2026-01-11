import { BaseMCPTool } from '../core/base-tool';
import { MCPContext, MCPToolResult } from '../core/types';

export class TabsTool extends BaseMCPTool {
  definition = {
    name: 'browser_tabs',
    description: 'List, create, close, or select browser tabs',
    inputSchema: {
      type: 'object' as const,
      properties: {
        action: { type: 'string', description: 'Tab operation to perform', enum: ['list', 'new', 'close', 'select'] },
        index: { type: 'number', description: 'Tab index for close/select operations', minimum: 0 },
        url: { type: 'string', description: 'URL for new tab', format: 'uri' }
      },
      required: ['action']
    },
    metadata: { tags: ['browser', 'tabs', 'management'] }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { action, index, url } = args;
    const { page, context: browserContext } = context;

    switch (action) {
      case 'list': {
        const pages = browserContext.pages();
        const currentIndex = pages.indexOf(page);
        const tabs = await Promise.all(pages.map(async (p: any, i: number) => ({
          index: i,
          url: p.url(),
          title: await p.title(),
          active: i === currentIndex
        })));

        return {
          content: [{ type: 'text', text: `Browser tabs (${tabs.length} total):\n${JSON.stringify(tabs, null, 2)}` }]
        };
      }

      case 'new': {
        const newPage = await browserContext.newPage();
        if (url) {
          await newPage.goto(url);
        }
        return this.textResult(`Created new tab${url ? ` and navigated to ${url}` : ''}`);
      }

      case 'close': {
        if (index !== undefined) {
          const pages = browserContext.pages();
          if (index >= 0 && index < pages.length) {
            await pages[index].close();
            return this.textResult(`Closed tab at index ${index}`);
          }
          return this.errorResult(`Invalid tab index: ${index}`);
        }
        await page.close();
        return this.textResult('Closed current tab');
      }

      case 'select': {
        if (index !== undefined) {
          const pages = browserContext.pages();
          if (index >= 0 && index < pages.length) {
            await pages[index].bringToFront();
            return this.textResult(`Switched to tab at index ${index}`);
          }
          return this.errorResult(`Invalid tab index: ${index}`);
        }
        return this.errorResult('Tab index required for select action');
      }

      default:
        return this.errorResult(`Unknown action: ${action}`);
    }
  }
}

export class ResizeTool extends BaseMCPTool {
  definition = {
    name: 'browser_resize',
    description: 'Resize the browser window to specified dimensions',
    inputSchema: {
      type: 'object' as const,
      properties: {
        width: { type: 'number', description: 'Window width in pixels', minimum: 100, maximum: 10000 },
        height: { type: 'number', description: 'Window height in pixels', minimum: 100, maximum: 10000 }
      },
      required: ['width', 'height']
    },
    metadata: { tags: ['browser', 'window', 'resize'] }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { width, height } = args;
    const { page } = context;
    await page.setViewportSize({ width, height });
    return this.textResult(`Browser window resized to ${width}x${height}`);
  }
}

export class HandleDialogTool extends BaseMCPTool {
  definition = {
    name: 'browser_handle_dialog',
    description: 'Handle JavaScript dialogs (alert, confirm, prompt)',
    inputSchema: {
      type: 'object' as const,
      properties: {
        accept: { type: 'boolean', description: 'Whether to accept (OK) or dismiss (Cancel) the dialog', default: true },
        promptText: { type: 'string', description: 'Text to enter for prompt dialogs' }
      },
      required: []
    },
    metadata: { tags: ['browser', 'dialog', 'alert'] }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { accept = true, promptText } = args;
    const { page } = context;

    page.once('dialog', async (dialog: any) => {
      if (promptText && dialog.type() === 'prompt') {
        await dialog.accept(promptText);
      } else if (accept) {
        await dialog.accept();
      } else {
        await dialog.dismiss();
      }
    });

    return this.textResult(`Dialog handler configured (accept: ${accept}${promptText ? `, prompt: ${promptText}` : ''})`);
  }
}

export class ReloadTool extends BaseMCPTool {
  definition = {
    name: 'browser_reload',
    description: 'Reload the current page',
    inputSchema: {
      type: 'object' as const,
      properties: {
        force: { type: 'boolean', description: 'Whether to force reload from server (bypass cache)', default: false },
        waitUntil: { type: 'string', description: 'When to consider reload complete', enum: ['load', 'domcontentloaded', 'networkidle'], default: 'load' }
      },
      required: []
    },
    metadata: { tags: ['browser', 'reload', 'refresh'] }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { force = false, waitUntil = 'load' } = args;
    const { page } = context;

    await page.reload({ waitUntil: waitUntil as any, timeout: 30000 });
    const pageTitle = await page.title();

    return this.textResult(`Page reloaded${force ? ' (forced)' : ''}. Title: ${pageTitle}`);
  }
}

export class CloseTool extends BaseMCPTool {
  definition = {
    name: 'browser_close',
    description: 'Close the browser or current page',
    inputSchema: {
      type: 'object' as const,
      properties: {
        closeBrowser: { type: 'boolean', description: 'Whether to close entire browser (true) or just current page (false)', default: false }
      },
      required: []
    },
    metadata: { tags: ['browser', 'close'], destructive: true }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { closeBrowser = false } = args;
    const { page, context: browserContext } = context;

    if (closeBrowser) {
      await browserContext.browser()?.close();
      return this.textResult('Browser closed');
    } else {
      await page.close();
      return this.textResult('Current page closed');
    }
  }
}