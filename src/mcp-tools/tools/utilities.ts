/**
 * Utility MCP Tools
 * Tools for waiting, evaluating, and other utilities
 */

import { BaseMCPTool } from '../core/base-tool';
import { MCPContext, MCPToolResult } from '../core/types';
import { Page } from 'playwright';

type WaitState = 'attached' | 'detached' | 'visible' | 'hidden';

type RequestRecord = {
  url: string;
  method: string;
  status?: number;
  resourceType: string;
  size?: number;
  failureText?: string;
  timestamp: number;
};

type ConsoleRecord = {
  type: string;
  text: string;
  location?: {
    url?: string;
    lineNumber?: number;
    columnNumber?: number;
  };
  args?: string[];
  timestamp: number;
  weight: number;
};

const MAX_TRACKED_ENTRIES = 2000;

const requestRecords = new WeakMap<Page, RequestRecord[]>();
const consoleRecords = new WeakMap<Page, ConsoleRecord[]>();

const levelWeights: Record<string, number> = {
  debug: 0,
  trace: 0,
  log: 1,
  info: 1,
  warn: 2,
  warning: 2,
  error: 3
};

const severityThreshold: Record<'debug' | 'info' | 'warning' | 'error', number> = {
  debug: 0,
  info: 1,
  warning: 2,
  error: 3
};

function trimRecords<T>(records: T[]) {
  if (records.length > MAX_TRACKED_ENTRIES) {
    records.splice(0, records.length - MAX_TRACKED_ENTRIES);
  }
}

function ensureRequestTracking(page: Page) {
  if (requestRecords.has(page)) {
    return;
  }

  const records: RequestRecord[] = [];
  requestRecords.set(page, records);

  const recordEntry = (entry: RequestRecord) => {
    const store = requestRecords.get(page);
    if (!store) {
      return;
    }
    store.push(entry);
    trimRecords(store);
  };

  page.on('requestfinished', async request => {
    try {
      const response = await request.response();
      const headers = response?.headers() ?? {};
      const sizeHeader = headers['content-length'];
      const size = sizeHeader && !Number.isNaN(Number(sizeHeader))
        ? Number(sizeHeader)
        : undefined;

      recordEntry({
        url: request.url(),
        method: request.method(),
        status: response?.status(),
        resourceType: request.resourceType(),
        size,
        timestamp: Date.now()
      });
    } catch {
      recordEntry({
        url: request.url(),
        method: request.method(),
        resourceType: request.resourceType(),
        timestamp: Date.now()
      });
    }
  });

  page.on('requestfailed', request => {
    recordEntry({
      url: request.url(),
      method: request.method(),
      resourceType: request.resourceType(),
      failureText: request.failure()?.errorText,
      timestamp: Date.now()
    });
  });

  page.once('close', () => requestRecords.delete(page));
}

function ensureConsoleTracking(page: Page) {
  if (consoleRecords.has(page)) {
    return;
  }

  const records: ConsoleRecord[] = [];
  consoleRecords.set(page, records);

  page.on('console', async message => {
    const type = message.type();
    const weight = levelWeights[type] ?? 1;
    const entry: ConsoleRecord = {
      type,
      text: message.text(),
      location: message.location(),
      timestamp: Date.now(),
      weight
    };

    const args = message.args();
    if (args.length) {
      entry.args = await Promise.all(args.map(async handle => {
        try {
          const value = await handle.jsonValue();
          return typeof value === 'string' ? value : JSON.stringify(value);
        } catch {
          return handle.toString();
        }
      }));
    }

    const store = consoleRecords.get(page);
    if (!store) {
      return;
    }
    store.push(entry);
    trimRecords(store);
  });

  page.once('close', () => consoleRecords.delete(page));
}

/**
 * Wait for a condition or time
 */
export class WaitTool extends BaseMCPTool {
  definition = {
    name: 'browser_wait',
    description: 'Wait for a specified time, text to appear/disappear, or element',
    inputSchema: {
      type: 'object' as const,
      properties: {
        time: {
          type: 'number',
          description: 'Wait time in seconds (0.1 to 300)',
          minimum: 0.1,
          maximum: 300
        },
        text: {
          type: 'string',
          description: 'Text to wait for on the page'
        },
        textGone: {
          type: 'string',
          description: 'Text to wait for to disappear from the page'
        },
        selector: {
          type: 'string',
          description: 'CSS selector to wait for element to appear'
        },
        state: {
          type: 'string',
          description: 'Element state to wait for',
          enum: ['attached', 'detached', 'visible', 'hidden'],
          default: 'visible'
        },
        timeout: {
          type: 'number',
          description: 'Maximum wait time in seconds',
          minimum: 1,
          maximum: 300,
          default: 30
        }
      },
      required: []
    },
    metadata: {
      tags: ['utility', 'wait', 'timeout']
    }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const {
      time,
      text,
      textGone,
      selector,
      state = 'visible',
      timeout = 30
    } = args;

    const { page } = context;
    const timeoutMs = timeout * 1000;

    if (time) {
      await page.waitForTimeout(time * 1000);
      return this.textResult(`Waited ${time} second(s)`);
    }

    if (text) {
      const textLocator = page.getByText(text, { exact: false }).first();
      await textLocator.waitFor({ state: 'visible', timeout: timeoutMs });
      return this.textResult(`Waited for text to appear: '${text}'`);
    }

    if (textGone) {
      const textLocator = page.getByText(textGone, { exact: false }).first();
      await textLocator.waitFor({ state: 'hidden', timeout: timeoutMs });
      return this.textResult(`Waited for text to disappear: '${textGone}'`);
    }

    if (selector) {
      const waitState = state as WaitState;
      const element = page.locator(selector).first();
      await element.waitFor({ state: waitState, timeout: timeoutMs });
      return this.textResult(`Waited for element: ${selector} (state: ${waitState})`);
    }

    return this.errorResult('No valid wait condition provided. Use time, text, textGone, or selector.');
  }
}

/**
 * Execute JavaScript in page context
 */
export class EvaluateTool extends BaseMCPTool {
  definition = {
    name: 'browser_evaluate',
    description: 'Execute JavaScript code in the browser page context',
    inputSchema: {
      type: 'object' as const,
      properties: {
        script: {
          type: 'string',
          description: 'JavaScript code to execute'
        },
        waitForFunction: {
          type: 'boolean',
          description: 'Whether to wait for the script to return a truthy value',
          default: false
        },
        timeout: {
          type: 'number',
          description: 'Maximum time to wait for function in seconds',
          minimum: 1,
          maximum: 300,
          default: 30
        }
      },
      required: ['script']
    },
    metadata: {
      tags: ['utility', 'javascript', 'evaluate'],
      idempotent: true
    }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { script, waitForFunction = false, timeout = 30 } = args;
    const { page } = context;

    let result: any;

    try {
      if (waitForFunction) {
        result = await page.waitForFunction(
          new Function('return ' + script),
          { timeout: timeout * 1000 }
        );
      } else {
        result = await page.evaluate(new Function('return ' + script));
      }

      const resultText = typeof result === 'object'
        ? JSON.stringify(result, null, 2)
        : String(result);

      return {
        content: [{
          type: 'text',
          text: `JavaScript executed successfully.\nResult: ${resultText}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: 'text',
          text: `JavaScript execution failed: ${error instanceof Error ? error.message : 'Unknown error'}`
        }],
        isError: true
      };
    }
  }
}

/**
 * Get page snapshot (accessibility tree)
 */
export class GetSnapshotTool extends BaseMCPTool {
  definition = {
    name: 'browser_get_snapshot',
    description: 'Get accessibility snapshot of the current page for element identification',
    inputSchema: {
      type: 'object' as const,
      properties: {
        root: {
          type: 'string',
          description: 'CSS selector to limit snapshot to a specific subtree',
          default: 'body'
        }
      },
      required: []
    },
    metadata: {
      tags: ['utility', 'snapshot', 'accessibility'],
      idempotent: true
    }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { root = 'body' } = args;
    const { page } = context;

    const snapshot = await page.locator(root).first().ariaSnapshot();
    const serialized = JSON.stringify(snapshot, null, 2);

    return {
      content: [{
        type: 'text',
        text: `Page snapshot:\n${serialized}`
      }]
    };
  }
}

/**
 * Get network requests
 */
export class GetNetworkRequestsTool extends BaseMCPTool {
  definition = {
    name: 'browser_get_network_requests',
    description: 'Get all network requests made since page load',
    inputSchema: {
      type: 'object' as const,
      properties: {
        includeStatic: {
          type: 'boolean',
          description: 'Whether to include static resources (images, fonts, scripts)',
          default: false
        },
        filter: {
          type: 'string',
          description: 'Filter requests by URL pattern (regex)'
        },
        limit: {
          type: 'number',
          description: 'Maximum number of requests to return',
          minimum: 1,
          maximum: 1000,
          default: 100
        }
      },
      required: []
    },
    metadata: {
      tags: ['utility', 'network', 'requests'],
      idempotent: true
    }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { includeStatic = false, filter, limit = 100 } = args;
    const { page } = context;

    ensureRequestTracking(page);
    let recorded = [...(requestRecords.get(page) ?? [])];

    if (!includeStatic) {
      const staticExtensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf'];
      recorded = recorded.filter(req => {
        const url = req.url.toLowerCase();
        return !staticExtensions.some(ext => url.includes(ext));
      });
    }

    if (filter) {
      let regex: RegExp;
      try {
        regex = new RegExp(filter, 'i');
      } catch {
        return this.errorResult(`Invalid filter regex: ${filter}`);
      }
      recorded = recorded.filter(req => regex.test(req.url));
    }

    const limited = recorded.slice(-limit);

    const summary = limited.map(req => ({
      url: req.url,
      method: req.method,
      status: req.status ?? (req.failureText ? 'failed' : 'pending'),
      type: req.resourceType,
      size: req.size ?? null,
      failure: req.failureText,
      timestamp: req.timestamp
    }));

    return {
      content: [{
        type: 'text',
        text: `Network requests (${summary.length} total):\n${JSON.stringify(summary, null, 2)}`
      }]
    };
  }
}

/**
 * Get console messages
 */
export class GetConsoleMessagesTool extends BaseMCPTool {
  definition = {
    name: 'browser_get_console_messages',
    description: 'Get console messages from the browser',
    inputSchema: {
      type: 'object' as const,
      properties: {
        level: {
          type: 'string',
          description: 'Minimum log level to retrieve',
          enum: ['error', 'warning', 'info', 'debug'],
          default: 'info'
        },
        limit: {
          type: 'number',
          description: 'Maximum number of messages to retrieve',
          minimum: 1,
          maximum: 1000,
          default: 100
        }
      },
      required: []
    },
    metadata: {
      tags: ['utility', 'console', 'logs'],
      idempotent: true
    }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { level = 'info', limit = 100 } = args;
    const { page } = context;

    ensureConsoleTracking(page);
    const severity = severityThreshold[level as keyof typeof severityThreshold];
    const messages = (consoleRecords.get(page) ?? []).filter(entry => entry.weight >= severity);
    const limited = messages.slice(-limit);

    const summary = limited.map(msg => ({
      type: msg.type,
      text: msg.text,
      location: msg.location,
      args: msg.args,
      timestamp: msg.timestamp
    }));

    return {
      content: [{
        type: 'text',
        text: `Console messages (${summary.length} total, level >= ${level}):\n${JSON.stringify(summary, null, 2)}`
      }]
    };
  }
}