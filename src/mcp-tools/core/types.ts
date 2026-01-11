/**
 * MCP Tool Base Interface
 * Following MCP specification for tool definitions
 */

export interface MCPToolSchema {
  type: 'object';
  properties: Record<string, {
    type: string;
    description?: string;
    enum?: any[];
    format?: string;
    pattern?: string;
    minimum?: number;
    maximum?: number;
    minLength?: number;
    maxLength?: number;
    default?: any;
  }>;
  required: string[];
  additionalProperties?: boolean;
}

export interface MCPToolDefinition {
  name: string;
  description: string;
  inputSchema: MCPToolSchema;
  metadata?: {
    tags?: string[];
    rateLimit?: number;
    idempotent?: boolean;
    destructive?: boolean;
    requiresAuth?: boolean;
    resources?: string[];
  };
}

export interface MCPToolResult {
  content: Array<{
    type: 'text' | 'image' | 'resource';
    text?: string;
    data?: string;
    mimeType?: string;
    resource?: {
      uri: string;
      name?: string;
      description?: string;
      mimeType?: string;
    };
  }>;
  isError?: boolean;
  _meta?: {
    progress?: number;
    total?: number;
    [key: string]: any;
  };
}

export interface MCPTool {
  definition: MCPToolDefinition;
  execute(args: any, context: any): Promise<MCPToolResult>;
}

export interface MCPContext {
  page: any; // Playwright Page
  context: any; // Playwright BrowserContext
  profile?: string;
  sessionId?: string;
}

export type ToolHandler = (args: any, context: MCPContext) => Promise<MCPToolResult>;