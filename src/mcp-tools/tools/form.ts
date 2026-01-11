/**
 * Form MCP Tools
 * Tools for working with HTML forms
 */

import { BaseMCPTool } from '../core/base-tool';
import { MCPContext, MCPToolResult } from '../core/types';
import { Locator, Page, BrowserContext } from 'playwright';

/**
 * Fill multiple form fields at once
 */
export class FillFormTool extends BaseMCPTool {
  definition = {
    name: 'browser_fill_form',
    description: 'Fill multiple form fields with provided values',
    inputSchema: {
      type: 'object' as const,
      properties: {
        fields: {
          type: 'array',
          description: 'Array of fields to fill with their values',
          items: {
            type: 'object' as const,
            properties: {
              name: {
                type: 'string',
                description: 'Field label or placeholder text (falls back to name attribute)'
              },
              type: {
                type: 'string',
                description: 'Field type (textbox, checkbox, radio, combobox, slider)',
                enum: ['textbox', 'checkbox', 'radio', 'combobox', 'slider']
              },
              value: {
                description: 'Value to set for the field'
              }
            },
            required: ['name', 'type', 'value']
          }
        },
        submit: {
          type: 'boolean',
          description: 'Whether to submit the form after filling',
          default: false
        },
        timeout: {
          type: 'number',
          description: 'Maximum time to wait for each field in milliseconds',
          minimum: 0,
          maximum: 60000,
          default: 5000
        }
      },
      required: ['fields']
    },
    metadata: {
      tags: ['form', 'input', 'fill']
    }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { fields, submit = false, timeout = 5000 } = args;
    const { page } = context;

    const results: string[] = [];

    for (const field of fields) {
      const { name, type, value } = field;

      try {
        switch (type) {
          case 'textbox': {
            const textbox = await this.resolveFieldLocator(
              page,
              [name],
              timeout,
              [() => page.locator(`input[name="${name}"], textarea[name="${name}"], [id="${name}"]`).first()]
            );
            const stringValue = value !== undefined && value !== null ? String(value) : '';
            await textbox.fill(stringValue);
            results.push(`Filled textbox ${name} with: ${stringValue}`);
            break;
          }

          case 'checkbox': {
            const checkbox = await this.resolveFieldLocator(
              page,
              [name],
              timeout,
              [() => page.locator(`input[type="checkbox"][name="${name}"], [id="${name}"][type="checkbox"]`).first()]
            );
            if (value) {
              await checkbox.check();
              results.push(`Checked checkbox: ${name}`);
            } else {
              await checkbox.uncheck();
              results.push(`Unchecked checkbox: ${name}`);
            }
            break;
          }

          case 'radio': {
            const radioValue = Array.isArray(value) ? value[0] : value;
            const radio = await this.resolveFieldLocator(
              page,
              [typeof radioValue === 'string' ? radioValue : undefined, name],
              timeout,
              [
                () =>
                  page
                    .locator(
                      `input[type="radio"][name="${name}"]${
                        radioValue !== undefined && radioValue !== null ? `[value="${radioValue}"]` : ''
                      }`
                    )
                    .first()
              ]
            );
            await radio.check();
            results.push(`Selected radio ${name}: ${radioValue}`);
            break;
          }

          case 'combobox': {
            const combobox = await this.resolveFieldLocator(
              page,
              [name],
              timeout,
              [() => page.locator(`select[name="${name}"], [id="${name}"]`).first()]
            );
            await combobox.selectOption(value);
            results.push(`Selected option from ${name}: ${Array.isArray(value) ? value.join(', ') : value}`);
            break;
          }

          case 'slider': {
            const slider = await this.resolveFieldLocator(
              page,
              [name],
              timeout,
              [() => page.locator(`input[type="range"][name="${name}"], [id="${name}"][type="range"]`).first()]
            );
            const sliderValue = value !== undefined && value !== null ? String(value) : '';
            await slider.fill(sliderValue);
            results.push(`Set slider ${name} to: ${sliderValue}`);
            break;
          }

          default:
            results.push(`Unknown field type: ${type} for ${name}`);
        }
      } catch (error) {
        results.push(`Failed to fill ${name}: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    }

    if (submit) {
      const submitLocators: Array<() => Locator> = [
        () => page.getByRole('button', { name: /submit/i }).first(),
        () => page.locator('input[type="submit"], button[type="submit"]').first()
      ];

      let submitted = false;
      for (const createLocator of submitLocators) {
        const locator = createLocator();
        try {
          await locator.waitFor({ timeout });
          await locator.click();
          submitted = true;
          results.push('Form submitted');
          break;
        } catch {
          continue;
        }
      }

      if (!submitted) {
        throw new Error('Unable to locate submit button');
      }
    }

    return this.textResult(`Form filled successfully:\n${results.join('\n')}`);
  }

  private async resolveFieldLocator(
    page: Page,
    identifiers: Array<string | undefined>,
    timeout: number,
    fallbackLocators: Array<() => Locator> = []
  ): Promise<Locator> {
    const uniqueIdentifiers = Array.from(
      new Set(
        identifiers.filter(
          (identifier): identifier is string => typeof identifier === 'string' && identifier.trim().length > 0
        )
      )
    );

    const locatorFactories: Array<() => Locator> = [];

    for (const identifier of uniqueIdentifiers) {
      locatorFactories.push(
        () => page.getByLabel(identifier, { exact: true }).first(),
        () => page.getByLabel(identifier, { exact: false }).first(),
        () => page.getByPlaceholder(identifier, { exact: true }).first(),
        () => page.getByPlaceholder(identifier, { exact: false }).first()
      );
    }

    locatorFactories.push(...fallbackLocators);

    for (const factory of locatorFactories) {
      const locator = factory();
      try {
        await locator.waitFor({ timeout });
        return locator;
      } catch {
        continue;
      }
    }

    const identifierMessage = uniqueIdentifiers.length > 0 ? uniqueIdentifiers.join(', ') : 'no accessible identifiers';
    throw new Error(`Unable to locate field using ${identifierMessage}`);
  }
}

/**
 * Get form data
 */
export class GetFormDataTool extends BaseMCPTool {
  definition = {
    name: 'browser_get_form_data',
    description: 'Extract all form data and field values from the current page',
    inputSchema: {
      type: 'object' as const,
      properties: {
        formSelector: {
          type: 'string',
          description: 'CSS selector for specific form (default: first form on page)',
          default: 'form'
        },
        includeEmpty: {
          type: 'boolean',
          description: 'Whether to include empty fields in the result',
          default: false
        }
      },
      required: []
    },
    metadata: {
      tags: ['form', 'data', 'extract'],
      idempotent: true
    }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const { formSelector = 'form', includeEmpty = false } = args;
    const { page } = context;

    const formData = await page.evaluate((selector: string, includeEmptyFields: boolean) => {
      const form = document.querySelector(selector) as HTMLFormElement;
      if (!form) {
        return { error: `Form not found: ${selector}` };
      }

      const data: any = {};
      const elements = form.elements;

      for (let i = 0; i < elements.length; i++) {
        const element = elements[i] as any;
        const name = element.name || element.id;

        if (!name) continue;

        let value: any = null;
        let type = element.type || element.tagName.toLowerCase();

        switch (type) {
          case 'input':
            switch (element.type) {
              case 'checkbox':
                value = element.checked;
                break;
              case 'radio':
                if (element.checked) value = element.value;
                break;
              case 'file':
                value = element.files.length > 0 ? Array.from(element.files).map((f: any) => f.name) : [];
                break;
              default:
                value = element.value;
            }
            break;

          case 'textarea':
            value = element.value;
            break;

          case 'select':
            if (element.multiple) {
              value = Array.from(element.selectedOptions).map((opt: any) => opt.value);
            } else {
              value = element.value;
            }
            break;

          default:
            value = element.value;
        }

        if (includeEmptyFields || value !== null && value !== '' && value !== false) {
          data[name] = {
            type: element.type || type,
            value,
            id: element.id,
            className: element.className
          };
        }
      }

      return {
        formAction: form.action,
        formMethod: form.method || 'GET',
        fields: data
      };
    }, formSelector, includeEmpty);

    if (formData.error) {
      return this.errorResult(formData.error);
    }

    return {
      content: [{
        type: 'text',
        text: `Form data extracted:\n${JSON.stringify(formData, null, 2)}`
      }]
    };
  }
}

/**
 * Submit a form
 */
export class SubmitFormTool extends BaseMCPTool {
  definition = {
    name: 'browser_submit_form',
    description: 'Submit a form by clicking submit button or calling form.submit()',
    inputSchema: {
      type: 'object' as const,
      properties: {
        formSelector: {
          type: 'string',
          description: 'CSS selector for the form to submit',
          default: 'form'
        },
        submitSelector: {
          type: 'string',
          description: 'CSS selector for submit button (optional, uses default submit if not provided)'
        },
        waitForNavigation: {
          type: 'boolean',
          description: 'Whether to wait for navigation after submission',
          default: true
        },
        timeout: {
          type: 'number',
          description: 'Maximum time to wait for navigation in milliseconds',
          minimum: 0,
          maximum: 300000,
          default: 30000
        }
      },
      required: []
    },
    metadata: {
      tags: ['form', 'submit', 'action']
    }
  };

  protected async _execute(args: any, context: MCPContext): Promise<MCPToolResult> {
    const {
      formSelector = 'form',
      submitSelector,
      waitForNavigation = true,
      timeout = 30000
    } = args;

    const { page } = context;

    try {
      const submitForm = async () => {
        if (submitSelector) {
          // Click specific submit button
          const button = page.locator(submitSelector).first();
          await button.waitFor({ timeout });
          await button.click();
        } else {
          // Use default form submission
          await page.waitForSelector(formSelector, { timeout });
          await page.evaluate((selector: string) => {
            const form = document.querySelector(selector) as HTMLFormElement;
            if (form) form.submit();
            else throw new Error(`Form not found: ${selector}`);
          }, formSelector);
        }
      };

      if (waitForNavigation) {
        const navigationPromise = page.waitForNavigation({ timeout });
        await Promise.all([navigationPromise, submitForm()]);
      } else {
        await submitForm();
      }

      return {
        content: [{
          type: 'text',
          text: `Form submitted successfully. Current URL: ${page.url()}`
        }]
      };
    } catch (error) {
      return this.errorResult(`Failed to submit form: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
}