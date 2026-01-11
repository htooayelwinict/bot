import { MCPTool, MCPToolDefinition, MCPToolResult, MCPContext } from './types';
import { Page, BrowserContext } from 'playwright';

export abstract class BaseMCPTool implements MCPTool {
  abstract definition: MCPToolDefinition;

  constructor(private page?: Page, private context?: BrowserContext) {}

  async execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const validation = this.validateArguments(args);
    if (!validation.valid) {
      return {
        content: [{ type: 'text', text: `Argument validation failed: ${validation.errors.join(', ')}` }],
        isError: true
      };
    }

    const page = context.page || this.page;
    const ctx = context.context || this.context;

    if (!page || !ctx) {
      return {
        content: [{ type: 'text', text: 'No browser page/context available' }],
        isError: true
      };
    }

    try {
      return await this._execute(args, { page, context: ctx, profile: context.profile, sessionId: context.sessionId });
    } catch (error) {
      return {
        content: [{ type: 'text', text: `Tool execution failed: ${error instanceof Error ? error.message : 'Unknown error'}` }],
        isError: true
      };
    }
  }

  protected abstract _execute(args: any, context: MCPContext): Promise<MCPToolResult>;

  private validateArguments(args: any): { valid: boolean; errors: string[] } {
    const schema = this.definition.inputSchema;
    const errors: string[] = [];

    for (const required of schema.required || []) {
      if (!(required in args)) {
        errors.push(`Missing required property: ${required}`);
      }
    }

    if (schema.properties) {
      for (const [key, value] of Object.entries(args)) {
        const propSchema = schema.properties[key];

        if (!propSchema) {
          if (!schema.additionalProperties) {
            errors.push(`Unexpected property: ${key}`);
          }
          continue;
        }

        const typeCheck = (
          (propSchema.type === 'string' && typeof value !== 'string') ||
          (propSchema.type === 'number' && typeof value !== 'number') ||
          (propSchema.type === 'boolean' && typeof value !== 'boolean') ||
          (propSchema.type === 'array' && !Array.isArray(value))
        );

        if (typeCheck) {
          errors.push(`Property '${key}' must be ${propSchema.type}`);
        } else if (propSchema.enum && !propSchema.enum.includes(value)) {
          errors.push(`Property '${key}' must be one of: ${propSchema.enum.join(', ')}`);
        }
      }
    }

    return { valid: errors.length === 0, errors };
  }

  protected textResult(text: string): MCPToolResult {
    return { content: [{ type: 'text', text }] };
  }

  protected errorResult(message: string): MCPToolResult {
    return { content: [{ type: 'text', text: message }], isError: true };
  }

  setPageContext(page: Page, context: BrowserContext): void {
    this.page = page;
    this.context = context;
  }
}