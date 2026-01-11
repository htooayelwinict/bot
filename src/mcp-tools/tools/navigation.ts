import { BaseMCPTool } from '../core/base-tool';
import { MCPContext, MCPToolResult } from '../core/types';
import * as fs from 'fs/promises';
import * as path from 'path';

export class NavigateTool extends BaseMCPTool {
  definition = {
    name: 'browser_navigate',
    description: 'Navigate to a specific URL. Waits for the page to load before returning.',
    inputSchema: {
      type: 'object' as const,
      properties: {
        url: { type: 'string', description: 'The URL to navigate to', format: 'uri' },
        waitUntil: {
          type: 'string',
          description: 'When to consider navigation successful',
          enum: ['load', 'domcontentloaded', 'networkidle'],
          default: 'load'
        },
        timeout: {
          type: 'number',
          description: 'Maximum navigation time in milliseconds',
          minimum: 0,
          maximum: 300000,
          default: 30000
        }
      },
      required: ['url']
    },
    metadata: { tags: ['navigation', 'browser'], rateLimit: 10, idempotent: false }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { url, waitUntil = 'load', timeout = 30000 } = args;
    const { page } = context;

    await page.goto(url, { waitUntil: waitUntil as any, timeout });

    return {
      content: [{
        type: 'text',
        text: `Navigated to ${url}\nPage title: ${await page.title()}\nFinal URL: ${page.url()}`
      }]
    };
  }
}

export class NavigateBackTool extends BaseMCPTool {
  definition = {
    name: 'browser_navigate_back',
    description: 'Go back to the previous page in browser history',
    inputSchema: { type: 'object' as const, properties: {}, required: [] },
    metadata: { tags: ['navigation', 'browser'], idempotent: false }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { page } = context;
    await page.goBack();
    return this.textResult(`Navigated back. Current URL: ${page.url()}`);
  }
}

export class ScreenshotTool extends BaseMCPTool {
  definition = {
    name: 'browser_screenshot',
    description: 'Take a screenshot of the current page or a specific element',
    inputSchema: {
      type: 'object' as const,
      properties: {
        filename: { type: 'string', description: 'Screenshot filename (without extension)', pattern: '^[a-zA-Z0-9._-]+$' },
        type: { type: 'string', description: 'Screenshot image format', enum: ['png', 'jpeg'], default: 'png' },
        fullPage: { type: 'boolean', description: 'Whether to capture the full scrollable page', default: false },
        quality: { type: 'number', description: 'Image quality (1-100 for jpeg only)', minimum: 1, maximum: 100 },
        animations: { type: 'string', description: 'Control CSS animations', enum: ['allow', 'disabled'], default: 'disabled' },
        caret: { type: 'string', description: 'Control text cursor visibility', enum: ['hide', 'initial'], default: 'hide' },
        scale: { type: 'string', description: 'Screenshot scaling', enum: ['css', 'device'], default: 'css' },
        mask: { type: 'array', description: 'Array of CSS selectors to mask in the screenshot', items: { type: 'string' } }
      },
      required: []
    },
    metadata: { tags: ['screenshot', 'capture'], rateLimit: 5 }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const {
      filename = `screenshot-${Date.now()}`,
      type = 'png',
      fullPage = false,
      quality,
      animations = 'disabled',
      caret = 'hide',
      scale = 'css',
      mask
    } = args;

    const { page } = context;
    const screenshotDir = './screenshots';
    await fs.mkdir(screenshotDir, { recursive: true }).catch(() => {});

    const filePath = path.join(screenshotDir, `${filename}.${type}`);
    const screenshotOptions: any = {
      path: filePath,
      fullPage,
      type: type as any,
      animations: animations as any,
      caret: caret as any,
      scale: scale as any
    };

    if (type === 'jpeg' && quality) {
      screenshotOptions.quality = quality;
    }

    if (mask && Array.isArray(mask)) {
      screenshotOptions.mask = mask.map((selector: string) => page.locator(selector).first());
    }

    await page.screenshot(screenshotOptions);
    const stats = await fs.stat(filePath);
    const fileSizeKB = Math.round(stats.size / 1024);

    return {
      content: [{ type: 'text', text: `Screenshot saved to ${filePath} (${fileSizeKB} KB)` }],
      _meta: { filePath, fileSize: stats.size, type, fullPage, timestamp: new Date().toISOString() }
    };
  }
}

export class GetPageInfoTool extends BaseMCPTool {
  definition = {
    name: 'browser_get_page_info',
    description: 'Get information about the current page including URL, title, and meta information',
    inputSchema: { type: 'object' as const, properties: {}, required: [] },
    metadata: { tags: ['navigation', 'info'], idempotent: true }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { page } = context;

    const info = await page.evaluate(() => ({
      url: window.location.href,
      title: document.title,
      domain: window.location.hostname,
      path: window.location.pathname,
      readyState: document.readyState,
      scrollX: window.scrollX,
      scrollY: window.scrollY,
      viewport: { width: window.innerWidth, height: window.innerHeight }
    }));

    return { content: [{ type: 'text', text: JSON.stringify(info, null, 2) }] };
  }
}