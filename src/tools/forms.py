"""Form tools for browser automation.

Ported from src/mcp-tools/tools/form.ts
"""

import json
import re
from typing import Any, Callable, Literal, Optional

from playwright.async_api import Locator, Page
from pydantic import BaseModel, Field

from src.tools.base import ToolResult, async_session_tool

# ============= Tool Argument Schemas =============


class FormFieldArgs(BaseModel):
    """Single form field specification."""

    name: str = Field(description="Field label or placeholder text (falls back to name attribute)")
    type: Literal["textbox", "checkbox", "radio", "combobox", "slider"] = Field(
        description="Field type (textbox, checkbox, radio, combobox, slider)"
    )
    value: Any = Field(description="Value to set for the field")


class FillFormArgs(BaseModel):
    """Arguments for browser_fill_form tool."""

    fields: list[FormFieldArgs] = Field(description="Array of fields to fill with their values")
    submit: bool = Field(default=False, description="Whether to submit the form after filling")
    timeout: int = Field(
        default=5000,
        ge=0,
        le=60000,
        description="Maximum time to wait for each field in milliseconds",
    )


class GetFormDataArgs(BaseModel):
    """Arguments for browser_get_form_data tool."""

    form_selector: str = Field(
        default="form",
        description="CSS selector for specific form (default: first form on page)",
    )
    include_empty: bool = Field(
        default=False,
        description="Whether to include empty fields in the result",
    )


class SubmitFormArgs(BaseModel):
    """Arguments for browser_submit_form tool."""

    form_selector: str = Field(
        default="form",
        description="CSS selector for the form to submit",
    )
    submit_selector: Optional[str] = Field(
        default=None,
        description="CSS selector for submit button (optional, uses default submit if not provided)",
    )
    wait_for_navigation: bool = Field(
        default=True,
        description="Whether to wait for navigation after submission",
    )
    timeout: int = Field(
        default=30000,
        ge=0,
        le=300000,
        description="Maximum time to wait for navigation in milliseconds",
    )


# ============= Helpers =============


async def _resolve_field_locator(
    page: Page,
    identifiers: list[Optional[str]],
    timeout: int,
    fallback_locators: Optional[list[Callable[[], Locator]]] = None,
) -> Locator:
    unique_identifiers = [
        identifier.strip()
        for identifier in dict.fromkeys(identifiers)
        if isinstance(identifier, str) and identifier.strip()
    ]

    locator_factories: list[Callable[[], Locator]] = []

    for identifier in unique_identifiers:
        locator_factories.extend(
            [
                lambda ident=identifier: page.get_by_label(ident, exact=True).first,
                lambda ident=identifier: page.get_by_label(ident, exact=False).first,
                lambda ident=identifier: page.get_by_placeholder(ident, exact=True).first,
                lambda ident=identifier: page.get_by_placeholder(ident, exact=False).first,
            ]
        )

    if fallback_locators:
        locator_factories.extend(fallback_locators)

    for factory in locator_factories:
        locator = factory()
        try:
            await locator.wait_for(timeout=timeout)
            return locator
        except Exception:
            continue

    identifier_message = ", ".join(unique_identifiers) if unique_identifiers else "no accessible identifiers"
    raise ValueError(f"Unable to locate field using {identifier_message}")


# ============= Tool Functions =============


@async_session_tool
async def browser_fill_form(
    fields: list[dict],
    submit: bool = False,
    timeout: int = 5000,
    page: Page = None,
) -> str:
    """Fill multiple form fields with provided values."""
    results: list[str] = []

    try:
        for field in fields:
            name = field.get("name")
            field_type = field.get("type")
            value = field.get("value")

            try:
                if field_type == "textbox":
                    textbox = await _resolve_field_locator(
                        page,
                        [name],
                        timeout,
                        [
                            lambda: page.locator(
                                f'input[name="{name}"], textarea[name="{name}"], [id="{name}"]'
                            ).first
                        ],
                    )
                    string_value = "" if value is None else str(value)
                    await textbox.fill(string_value)
                    results.append(f"Filled textbox {name} with: {string_value}")
                elif field_type == "checkbox":
                    checkbox = await _resolve_field_locator(
                        page,
                        [name],
                        timeout,
                        [
                            lambda: page.locator(
                                f'input[type="checkbox"][name="{name}"], [id="{name}"][type="checkbox"]'
                            ).first
                        ],
                    )
                    if value:
                        await checkbox.check()
                        results.append(f"Checked checkbox: {name}")
                    else:
                        await checkbox.uncheck()
                        results.append(f"Unchecked checkbox: {name}")
                elif field_type == "radio":
                    radio_value = value[0] if isinstance(value, list) and value else value
                    radio = await _resolve_field_locator(
                        page,
                        [radio_value if isinstance(radio_value, str) else None, name],
                        timeout,
                        [
                            lambda: page.locator(
                                (
                                    f'input[type="radio"][name="{name}"]'
                                    + (f'[value="{radio_value}"]' if radio_value is not None else "")
                                )
                            ).first
                        ],
                    )
                    await radio.check()
                    results.append(f"Selected radio {name}: {radio_value}")
                elif field_type == "combobox":
                    combobox = await _resolve_field_locator(
                        page,
                        [name],
                        timeout,
                        [lambda: page.locator(f'select[name="{name}"], [id="{name}"]').first],
                    )
                    await combobox.select_option(value)
                    value_text = ", ".join(value) if isinstance(value, list) else value
                    results.append(f"Selected option from {name}: {value_text}")
                elif field_type == "slider":
                    slider = await _resolve_field_locator(
                        page,
                        [name],
                        timeout,
                        [
                            lambda: page.locator(
                                f'input[type="range"][name="{name}"], [id="{name}"][type="range"]'
                            ).first
                        ],
                    )
                    slider_value = "" if value is None else str(value)
                    await slider.fill(slider_value)
                    results.append(f"Set slider {name} to: {slider_value}")
                else:
                    results.append(f"Unknown field type: {field_type} for {name}")
            except Exception as field_error:
                results.append(f"Failed to fill {name}: {field_error}")

        if submit:
            submit_locators: list[Callable[[], Locator]] = [
                lambda: page.get_by_role("button", name=re.compile("submit", re.I)).first,
                lambda: page.locator('input[type="submit"], button[type="submit"]').first,
            ]

            submitted = False
            for create_locator in submit_locators:
                locator = create_locator()
                try:
                    await locator.wait_for(timeout=timeout)
                    await locator.click()
                    submitted = True
                    results.append("Form submitted")
                    break
                except Exception:
                    continue

            if not submitted:
                raise RuntimeError("Unable to locate submit button")

        return ToolResult(
            success=True,
            content="Form filled successfully:\n" + "\n".join(results),
            data={"results": results},
        ).to_string()
    except Exception as exc:
        return ToolResult(
            success=False,
            content=f"Error filling form: {exc}",
            data={"results": results},
        ).to_string()


@async_session_tool
async def browser_get_form_data(
    form_selector: str = "form",
    include_empty: bool = False,
    page: Page = None,
) -> str:
    """Extract all form data and field values from the current page."""
    try:
        script = """
        (args) => {
          const { selector, includeEmptyFields } = args;
          const form = document.querySelector(selector);
          if (!form) {
            return { error: `Form not found: ${selector}` };
          }

          const data = {};
          const elements = form.elements;

          for (let i = 0; i < elements.length; i++) {
            const element = elements[i];
            const name = element.name || element.id;

            if (!name) continue;

            let value = null;
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
                    value = element.files.length > 0 ? Array.from(element.files).map(f => f.name) : [];
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
                  value = Array.from(element.selectedOptions).map(opt => opt.value);
                } else {
                  value = element.value;
                }
                break;

              default:
                value = element.value;
            }

            if (includeEmptyFields || (value !== null && value !== '' && value !== false)) {
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
        }
        """

        form_data = await page.evaluate(
            script,
            {"selector": form_selector, "includeEmptyFields": include_empty},
        )

        if isinstance(form_data, dict) and form_data.get("error"):
            return ToolResult(success=False, content=form_data["error"]).to_string()

        return ToolResult(
            success=True,
            content=f"Form data extracted:\n{json.dumps(form_data, indent=2)}",
            data=form_data,
        ).to_string()
    except Exception as exc:
        return ToolResult(
            success=False,
            content=f"Failed to extract form data: {exc}",
        ).to_string()


@async_session_tool
async def browser_submit_form(
    form_selector: str = "form",
    submit_selector: Optional[str] = None,
    wait_for_navigation: bool = True,
    timeout: int = 30000,
    page: Page = None,
) -> str:
    """Submit a form by clicking submit button or calling form.submit()."""

    async def submit_form() -> None:
        if submit_selector:
            button = page.locator(submit_selector).first
            await button.wait_for(timeout=timeout)
            await button.click()
        else:
            await page.wait_for_selector(form_selector, timeout=timeout)
            await page.evaluate(
                """
                (selector) => {
                  const form = document.querySelector(selector);
                  if (form) form.submit();
                  else throw new Error(`Form not found: ${selector}`);
                }
                """,
                form_selector,
            )

    try:
        if wait_for_navigation:
            async with page.expect_navigation(timeout=timeout):
                await submit_form()
        else:
            await submit_form()

        return ToolResult(
            success=True,
            content=f"Form submitted successfully. Current URL: {page.url}",
            data={"url": page.url},
        ).to_string()
    except Exception as exc:
        return ToolResult(
            success=False,
            content=f"Failed to submit form: {exc}",
        ).to_string()
