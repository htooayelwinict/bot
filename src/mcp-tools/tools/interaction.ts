import { BaseMCPTool } from '../core/base-tool';
import { MCPContext, MCPToolResult } from '../core/types';

export class ClickTool extends BaseMCPTool {
  definition = {
    name: 'browser_click',
    description: 'Click on a web page element using CSS selector or text content',
    inputSchema: {
      type: 'object' as const,
      properties: {
        selector: { type: 'string', description: 'CSS selector, XPath, or text content to find the element' },
        button: { type: 'string', description: 'Mouse button to click', enum: ['left', 'right', 'middle'], default: 'left' },
        modifiers: { type: 'array', description: 'Modifier keys to hold during click', items: { type: 'string', enum: ['Alt', 'Control', 'ControlOrMeta', 'Meta', 'Shift'] } },
        doubleClick: { type: 'boolean', description: 'Whether to perform a double click', default: false },
        force: { type: 'boolean', description: 'Whether to bypass visibility checks', default: false },
        timeout: { type: 'number', description: 'Maximum time to wait for element in milliseconds', minimum: 0, maximum: 60000, default: 5000 }
      },
      required: ['selector']
    },
    metadata: { tags: ['interaction', 'click'], destructive: false }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { selector, button = 'left', modifiers = [], doubleClick = false, force = false, timeout = 5000 } = args;
    const { page } = context;
    const element = await page.locator(selector).first();
    await element.waitFor({ state: 'visible', timeout });

    const clickOptions = { button: button as any, modifiers: modifiers as any[], force };

    if (doubleClick) {
      await element.dblclick(clickOptions);
    } else {
      await element.click(clickOptions);
    }

    return this.textResult(`Clicked on element: ${selector}`);
  }
}

export class TypeTool extends BaseMCPTool {
  definition = {
    name: 'browser_type',
    description: 'Type text into an input field or editable element',
    inputSchema: {
      type: 'object' as const,
      properties: {
        selector: { type: 'string', description: 'CSS selector or XPath to find the input element' },
        text: { type: 'string', description: 'Text to type into the element' },
        clear: { type: 'boolean', description: 'Whether to clear the field before typing', default: true },
        submit: { type: 'boolean', description: 'Whether to submit the form after typing', default: false },
        delay: { type: 'number', description: 'Delay between keystrokes in milliseconds', minimum: 0, maximum: 1000, default: 0 },
        timeout: { type: 'number', description: 'Maximum time to wait for element in milliseconds', minimum: 0, maximum: 60000, default: 5000 }
      },
      required: ['selector', 'text']
    },
    metadata: { tags: ['interaction', 'type', 'input'] }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { selector, text, clear = true, submit = false, delay = 0, timeout = 5000 } = args;
    const { page } = context;
    const element = await page.locator(selector).first();
    await element.waitFor({ state: 'visible', timeout });

    if (clear) {
      await element.clear();
    }

    if (delay > 0) {
      await element.pressSequentially(text, { delay });
    } else {
      await element.fill(text);
    }

    if (submit) {
      await element.press('Enter');
    }

    return this.textResult(`Typed "${text}" into ${selector}${submit ? ' and submitted' : ''}`);
  }
}

export class SelectOptionTool extends BaseMCPTool {
  definition = {
    name: 'browser_select_option',
    description: 'Select one or more options from a dropdown select element',
    inputSchema: {
      type: 'object' as const,
      properties: {
        selector: { type: 'string', description: 'CSS selector to find the select element' },
        values: { type: 'array', description: 'Array of option values or text to select', items: { type: 'string' } },
        timeout: { type: 'number', description: 'Maximum time to wait for element in milliseconds', minimum: 0, maximum: 60000, default: 5000 }
      },
      required: ['selector', 'values']
    },
    metadata: { tags: ['interaction', 'select', 'dropdown'] }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { selector, values, timeout = 5000 } = args;
    const { page } = context;
    const element = await page.locator(selector).first();
    await element.waitFor({ state: 'visible', timeout });
    await element.selectOption(values);

    return this.textResult(`Selected ${values.length} option(s) from ${selector}: ${values.join(', ')}`);
  }
}

export class HoverTool extends BaseMCPTool {
  definition = {
    name: 'browser_hover',
    description: 'Hover the mouse over an element',
    inputSchema: {
      type: 'object' as const,
      properties: {
        selector: { type: 'string', description: 'CSS selector or XPath to find the element' },
        timeout: { type: 'number', description: 'Maximum time to wait for element in milliseconds', minimum: 0, maximum: 60000, default: 5000 }
      },
      required: ['selector']
    },
    metadata: { tags: ['interaction', 'hover', 'mouse'] }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { selector, timeout = 5000 } = args;
    const { page } = context;
    const element = await page.locator(selector).first();
    await element.waitFor({ state: 'visible', timeout });
    await element.hover();

    return this.textResult(`Hovered over element: ${selector}`);
  }
}

export class PressKeyTool extends BaseMCPTool {
  definition = {
    name: 'browser_press_key',
    description: 'Press a keyboard key or key combination',
    inputSchema: {
      type: 'object' as const,
      properties: {
        key: { type: 'string', description: 'Key to press (e.g., Enter, Escape, ArrowLeft, a, F1)' },
        modifiers: { type: 'array', description: 'Modifier keys to hold during key press', items: { type: 'string', enum: ['Alt', 'Control', 'ControlOrMeta', 'Meta', 'Shift'] } },
        delay: { type: 'number', description: 'Delay after key press in milliseconds', minimum: 0, maximum: 5000, default: 0 }
      },
      required: ['key']
    },
    metadata: { tags: ['interaction', 'keyboard', 'shortcut'] }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { key, modifiers = [], delay = 0 } = args;
    const { page } = context;

    await page.keyboard.press(key, { modifiers: modifiers as any[] });

    if (delay > 0) {
      await page.waitForTimeout(delay);
    }

    return this.textResult(`Pressed key: ${modifiers.join('+')}${modifiers.length > 0 ? '+' : ''}${key}`);
  }
}