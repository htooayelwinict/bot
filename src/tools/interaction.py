"""Interaction tools for browser automation.

Ported from src/mcp-tools/tools/interaction.ts
"""

from typing import Literal, Optional

from playwright.async_api import Page
from pydantic import BaseModel, Field, model_validator

from src.tools.base import ToolResult, async_session_tool

# ============= Tool Argument Schemas =============


class ClickArgs(BaseModel):
    """Arguments for browser_click tool."""

    ref: Optional[str] = Field(
        default=None,
        description="Exact element reference from page snapshot (preferred over selector)"
    )
    selector: Optional[str] = Field(
        default=None,
        description="CSS selector, XPath, or text content (fallback if ref not provided)"
    )
    button: Literal["left", "right", "middle"] = Field(
        default="left",
        description="Mouse button to click",
    )
    modifiers: list[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]] = Field(
        default_factory=list,
        description="Modifier keys to hold during click",
    )
    double_click: bool = Field(
        default=False,
        description="Whether to perform a double click",
    )
    force: bool = Field(
        default=False,
        description="Whether to bypass visibility checks",
    )
    timeout: int = Field(
        default=5000,
        ge=0,
        le=60000,
        description="Maximum time to wait for element in milliseconds",
    )

    @model_validator(mode="after")
    def require_selector_or_ref(self):
        if not self.selector and not self.ref:
            raise ValueError("Either 'selector' or 'ref' must be provided")
        return self


class TypeArgs(BaseModel):
    """Arguments for browser_type tool."""

    ref: Optional[str] = Field(
        default=None,
        description="Exact element reference from page snapshot (preferred over selector)"
    )
    selector: Optional[str] = Field(
        default=None,
        description="CSS selector or XPath to find the input element (fallback if ref not provided)"
    )
    text: str = Field(description="Text to type into the element")
    clear: bool = Field(default=True, description="Whether to clear the field before typing")
    submit: bool = Field(default=False, description="Whether to submit the form after typing")
    delay: int = Field(
        default=0,
        ge=0,
        le=1000,
        description="Delay between keystrokes in milliseconds",
    )
    timeout: int = Field(
        default=5000,
        ge=0,
        le=60000,
        description="Maximum time to wait for element in milliseconds",
    )

    @model_validator(mode="after")
    def require_selector_or_ref(self):
        if not self.selector and not self.ref:
            raise ValueError("Either 'selector' or 'ref' must be provided")
        return self


class SelectOptionArgs(BaseModel):
    """Arguments for browser_select_option tool."""

    ref: Optional[str] = Field(
        default=None,
        description="Exact element reference from page snapshot (preferred over selector)"
    )
    selector: Optional[str] = Field(
        default=None,
        description="CSS selector to find the select element (fallback if ref not provided)"
    )
    values: list[str] = Field(description="Array of option values or text to select")
    timeout: int = Field(
        default=5000,
        ge=0,
        le=60000,
        description="Maximum time to wait for element in milliseconds",
    )

    @model_validator(mode="after")
    def require_selector_or_ref(self):
        if not self.selector and not self.ref:
            raise ValueError("Either 'selector' or 'ref' must be provided")
        return self


class HoverArgs(BaseModel):
    """Arguments for browser_hover tool."""

    ref: Optional[str] = Field(
        default=None,
        description="Exact element reference from page snapshot (preferred over selector)"
    )
    selector: Optional[str] = Field(
        default=None,
        description="CSS selector or XPath to find the element (fallback if ref not provided)"
    )
    timeout: int = Field(
        default=5000,
        ge=0,
        le=60000,
        description="Maximum time to wait for element in milliseconds",
    )

    @model_validator(mode="after")
    def require_selector_or_ref(self):
        if not self.selector and not self.ref:
            raise ValueError("Either 'selector' or 'ref' must be provided")
        return self


class PressKeyArgs(BaseModel):
    """Arguments for browser_press_key tool."""

    key: str = Field(description="Key to press (e.g., Enter, Escape, ArrowLeft, a, F1)")
    modifiers: list[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]] = Field(
        default_factory=list,
        description="Modifier keys to hold during key press",
    )
    delay: int = Field(
        default=0,
        ge=0,
        le=5000,
        description="Delay after key press in milliseconds",
    )


# ============= Tool Functions =============


def _get_locator(page: Page, selector: str):
    """Get a Playwright locator using smart selector detection.

    Supports multiple selector strategies:
    - CSS selectors (default)
    - XPath (starts with // or xpath=)
    - Text content (starts with text= or "text:")
    - Role-based (starts with role=)
    - aria-label (starts with aria-label= or label=)
    - get_by_text for quoted strings
    - button= for button by name (accessibility name)
    - nth index: selector[nth=N] (0-indexed, e.g., div[nth=5])
    - hasText filter: selector:hasText("pattern") or selector:hasText(/regex/)
    - Combined: selector:hasText("pattern")[nth=N]

    Examples:
        div[nth=5]              -> 6th div element (0-indexed)
        div:hasText("Only me")   -> div containing "Only me"
        div:hasText(/^Only$/)    -> div matching regex
        div:hasText("Only me")[nth=5] -> 6th div containing "Only me"
    """
    selector = selector.strip()

    # Parse nth index and hasText filters before other processing
    nth_index = None
    has_text_pattern = None

    # Extract [nth=N] suffix
    import re
    nth_match = re.search(r'\[nth=(\d+)\]$', selector)
    if nth_match:
        nth_index = int(nth_match.group(1))
        selector = selector[:nth_match.start()].strip()

    # Extract :hasText(...) prefix/suffix
    has_text_match = re.search(r':hasText\(([^)]+)\)', selector)
    if has_text_match:
        has_text_pattern = has_text_match.group(1)
        selector = selector[:has_text_match.start()].strip()

    # Build base locator using existing logic
    locator = _get_base_locator(page, selector)

    # Apply hasText filter if present
    if has_text_pattern:
        # Check if it's a regex pattern (starts with /)
        if has_text_pattern.startswith('/'):
            # Extract regex from /pattern/ or /pattern/flags
            regex_parts = has_text_pattern[1:].rsplit('/', 1)
            if len(regex_parts) == 2:
                regex_pattern = regex_parts[0]
                # flags could be added here if needed
                locator = locator.filter(has_text=regex_pattern)
            else:
                locator = locator.filter(has_text=has_text_pattern[1:-1] if len(has_text_pattern) > 2 else has_text_pattern)
        else:
            # Remove quotes if present
            text = has_text_pattern.strip('"\'')
            locator = locator.filter(has_text=text)

    # Apply nth index if present, otherwise use .first for backward compatibility
    if nth_index is not None:
        locator = locator.nth(nth_index)
    elif has_text_pattern is None:
        # Only add .first if no nth/hasText modifiers (preserves existing behavior)
        locator = locator.first

    return locator


def _get_base_locator(page: Page, selector: str):
    """Get base locator without nth/hasText filters.

    This is called by _get_locator after extracting nth and hasText modifiers.
    See _get_locator for full selector syntax documentation.
    """
    selector = selector.strip()
    
    # XPath selector
    if selector.startswith("//") or selector.startswith("xpath="):
        xpath = selector.replace("xpath=", "", 1) if selector.startswith("xpath=") else selector
        return page.locator(f"xpath={xpath}").first
    
    # Button by name selector (matches button accessibility name)
    if selector.startswith("button="):
        name = selector.replace("button=", "", 1).strip()
        if (name.startswith('"') and name.endswith('"')) or (name.startswith("'") and name.endswith("'")):
            name = name[1:-1]
        return page.get_by_role("button", name=name).first
    
    # Radio button by label selector (for privacy dialogs, forms)
    if selector.startswith("radio="):
        label = selector.replace("radio=", "", 1).strip()
        if (label.startswith('"') and label.endswith('"')) or (label.startswith("'") and label.endswith("'")):
            label = label[1:-1]
        return page.get_by_role("radio", name=label).first
    
    # Checkbox by label selector
    if selector.startswith("checkbox="):
        label = selector.replace("checkbox=", "", 1).strip()
        if (label.startswith('"') and label.endswith('"')) or (label.startswith("'") and label.endswith("'")):
            label = label[1:-1]
        return page.get_by_role("checkbox", name=label).first
    
    # Link by text selector
    if selector.startswith("link="):
        text = selector.replace("link=", "", 1).strip()
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        return page.get_by_role("link", name=text).first
    
    # Text-based selector - try multiple strategies
    if selector.startswith("text=") or selector.startswith("text:"):
        text = selector.replace("text=", "", 1).replace("text:", "", 1).strip()
        # Remove quotes if present
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1]
        # First try get_by_text (for visible text)
        text_locator = page.get_by_text(text, exact=False).first
        # Also create button locator as fallback (for button accessibility names)
        button_locator = page.get_by_role("button", name=text).first
        # Return an or-locator that tries both
        return page.locator(f"text={text}").or_(page.get_by_role("button", name=text)).first
    
    # Role-based selector (e.g., role=button[name="Submit"] or role=button[name="Post"][exact])
    if selector.startswith("role="):
        role_part = selector.replace("role=", "", 1)
        # Parse role and optional name: role=button[name="Submit"]
        # Check for exact modifier: role=button[name="Post"][exact]
        exact_match = "[exact]" in role_part
        if exact_match:
            role_part = role_part.replace("[exact]", "")

        if "[name=" in role_part:
            role = role_part.split("[")[0]
            name_match = role_part.split('name="')[1].split('"')[0] if 'name="' in role_part else role_part.split("name='")[1].split("'")[0]
            locator = page.get_by_role(role, name=name_match, exact=exact_match)
        else:
            locator = page.get_by_role(role_part, exact=exact_match)
        return locator.first

    # Explicit textbox role helper (common for contenteditable fields)
    if selector == "textbox" or selector.startswith("role=textbox"):
        return page.get_by_role("textbox").first
    
    # aria-label selector
    if selector.startswith("aria-label=") or selector.startswith("label="):
        label = selector.replace("aria-label=", "", 1).replace("label=", "", 1).strip()
        if (label.startswith('"') and label.endswith('"')) or (label.startswith("'") and label.endswith("'")):
            label = label[1:-1]
        return page.get_by_label(label).first
    
    # Quoted string = text search
    if (selector.startswith('"') and selector.endswith('"')) or (selector.startswith("'") and selector.endswith("'")):
        text = selector[1:-1]
        return page.get_by_text(text, exact=False).first
    
    # Check for invalid jQuery-style selectors and convert
    if ":contains(" in selector:
        # Extract text from :contains('text') or :contains("text")
        import re
        match = re.search(r":contains\(['\"]([^'\"]+)['\"]\)", selector)
        if match:
            text = match.group(1)
            # Try to find element by text
            return page.get_by_text(text, exact=False).first
    
    # Default: CSS selector (return without .first to allow nth/hasText processing)
    return page.locator(selector)


@async_session_tool
async def browser_click(
    ref: str | None = None,
    selector: str | None = None,
    button: str = "left",
    modifiers: list[str] = None,
    double_click: bool = False,
    force: bool = False,
    timeout: int = 5000,
    page: Page = None,
) -> str:
    """Click on a web page element using ref or selector.

    PREFERRED: Use ref from browser_get_snapshot for precise targeting.
    FALLBACK: Use selector if ref not available.

    REF USAGE (recommended for disambiguation):
    1. Call browser_get_snapshot() to get element refs
    2. Find target ref (e.g., button "Post" [ref=e42])
    3. Call browser_click(ref="e42") for exact targeting

    SELECTOR USAGE (fallback):
    - button=Name: Clicks button with that accessible name (RECOMMENDED for buttons)
    - text=Text: Clicks element containing that text
    - radio=Text: Clicks radio button with that label
    - CSS selector: "button.submit", "#id", "[aria-label='Close']"
    - XPath: "//button[@type='submit']" or "xpath=//div"
    - nth index: "selector[nth=N]" (0-indexed)
    - hasText filter: "selector:hasText('text')" or "selector:hasText(/regex/)"

    Args:
        ref: Element reference from snapshot (e.g., "e42") - preferred
        selector: CSS/text/role selector - fallback
        button: Mouse button to click (left, right, middle)
        modifiers: Modifier keys to hold during click (Alt, Control, Meta, Shift)
        double_click: Whether to perform a double click
        force: Bypass actionability checks (use for modals/dialogs - RECOMMENDED)
        timeout: Maximum time to wait for element in milliseconds
        page: Playwright Page object (injected by decorator)

    Returns:
        Success message confirming the click action
    """
    from src.tools.ref_registry import resolve_ref, get_snapshot

    if modifiers is None:
        modifiers = []

    # Try ref resolution first (preferred path)
    if ref:
        try:
            element = await resolve_ref(page, ref)

            # Get element info for response
            snapshot_data = get_snapshot(page)
            element_info = {}
            if snapshot_data and ref in snapshot_data.refs:
                element_ref = snapshot_data.refs[ref]
                element_info = {
                    "ref": ref,
                    "role": element_ref.role,
                    "name": element_ref.name
                }

            click_options = {
                "button": button,
                "modifiers": modifiers,
                "force": force or True,  # Auto-force for refs (reliable)
                "timeout": timeout,
            }

            if double_click:
                await element.dblclick(**click_options)
            else:
                await element.click(**click_options)

            content = f"Clicked {element_info.get('role', 'element')}"
            if element_info.get('name'):
                content += f" '{element_info['name']}'"
            content += f" [ref={ref}]"

            return ToolResult(
                success=True,
                content=content,
                data={"ref": ref, "button": button, "double_click": double_click, "element": element_info},
            ).to_string()

        except ValueError as e:
            # If selector provided, fall through to selector-based click
            if selector:
                pass  # Continue to selector fallback
            else:
                return ToolResult(
                    success=False,
                    content=f"Ref resolution failed: {e}",
                    data={"ref": ref},
                ).to_string()

    # Selector-based click (fallback)
    if not selector:
        return ToolResult(
            success=False,
            content="Either 'ref' or 'selector' must be provided",
        ).to_string()

    try:
        element = _get_locator(page, selector)
        
        # Wait for element, but if force=True, don't require visibility
        if not force:
            await element.wait_for(state="visible", timeout=timeout)

        click_options = {
            "button": button,
            "modifiers": modifiers,
            "force": force,
            "timeout": timeout,
        }

        if double_click:
            await element.dblclick(**click_options)
        else:
            await element.click(**click_options)

        return ToolResult(
            success=True,
            content=f"Clicked on element: {selector}",
            data={"selector": selector, "button": button, "double_click": double_click, "force": force},
        ).to_string()
    except Exception as exc:
        error_msg = str(exc)
        # Provide helpful suggestions based on error type
        suggestion = ""
        if "intercepts pointer events" in error_msg:
            suggestion = " Try using force=True to bypass the intercepting element."
        elif "Timeout" in error_msg and "visible" in error_msg:
            suggestion = " Element not visible. Try a different selector or check if element exists."
        elif "SyntaxError" in error_msg or "not a valid selector" in error_msg:
            suggestion = " Invalid selector syntax. Use text='...' for text search or check CSS selector."
        
        return ToolResult(
            success=False,
            content=f"Click failed on '{selector}': {error_msg}{suggestion}",
            data={"selector": selector, "error": error_msg},
        ).to_string()


@async_session_tool
async def browser_type(
    ref: str | None = None,
    selector: str | None = None,
    text: str = "",
    clear: bool = True,
    submit: bool = False,
    delay: int = 0,
    timeout: int = 5000,
    page: Page = None,
) -> str:
    """Type text into an input field or editable element (including contenteditable).

    PREFERRED: Use ref from browser_get_snapshot for precise targeting.
    FALLBACK: Use selector if ref not available.

    REF USAGE (recommended for disambiguation):
    1. Call browser_get_snapshot() to get element refs
    2. Find target ref (e.g., textbox "Email" [ref=e23])
    3. Call browser_type(ref="e23", text="...") for exact targeting

    SELECTOR USAGE (fallback):
    - CSS selector: "input#email", "[name='password']", "div[role='textbox'] p"
    - XPath: "//input[@type='text']"
    - Role-based: 'role=textbox' (for contenteditable fields)
    - aria-label: 'aria-label=Search' or 'label=Search'

    NOTE: For rich text editors (Facebook, etc.), if typing fails, the tool
    automatically falls back to JavaScript to set the text and dispatch events.
    """
    from src.tools.ref_registry import resolve_ref, get_snapshot

    # Try ref resolution first (preferred path)
    if ref:
        try:
            element = await resolve_ref(page, ref)

            # Get element info for response
            snapshot_data = get_snapshot(page)
            element_info = {}
            if snapshot_data and ref in snapshot_data.refs:
                element_ref = snapshot_data.refs[ref]
                element_info = {
                    "ref": ref,
                    "role": element_ref.role,
                    "name": element_ref.name
                }

            # Focus and type
            await element.click(timeout=timeout)

            if clear:
                await element.fill("")

            if delay > 0:
                await element.press_sequentially(text, delay=delay)
            else:
                await element.fill(text)

            if submit:
                await element.press("Enter")

            content = f'Typed "{text}" into {element_info.get("role", "element")}'
            if element_info.get("name"):
                content += f" '{element_info['name']}'"
            content += f" [ref={ref}]"
            if submit:
                content += " and submitted"

            return ToolResult(
                success=True,
                content=content,
                data={"ref": ref, "text": text, "clear": clear, "submit": submit, "element": element_info},
            ).to_string()

        except ValueError as e:
            # If selector provided, fall through to selector-based typing
            if selector:
                pass  # Continue to selector fallback
            else:
                return ToolResult(
                    success=False,
                    content=f"Ref resolution failed: {e}",
                    data={"ref": ref},
                ).to_string()

    # Selector-based typing (fallback)
    if not selector:
        return ToolResult(
            success=False,
            content="Either 'ref' or 'selector' must be provided",
        ).to_string()

    try:
        element = _get_locator(page, selector)
        await element.wait_for(state="visible", timeout=timeout)

        # Try to focus the element first to help Playwright fill on rich text editors
        try:
            await element.click(timeout=timeout)
        except Exception:
            pass

        if clear:
            await element.fill("")

        if delay > 0:
            await element.press_sequentially(text, delay=delay)
        else:
            await element.fill(text)

        if submit:
            await element.press("Enter")

        return ToolResult(
            success=True,
            content=f'Typed "{text}" into {selector}{" and submitted" if submit else ""}',
            data={
                "selector": selector,
                "text": text,
                "clear": clear,
                "submit": submit,
                "delay": delay,
            },
        ).to_string()
    except Exception as exc:
        # Fallback for contenteditable/rich text areas that don't support fill/press
        try:
            element = _get_locator(page, selector)
            await element.wait_for(state="visible", timeout=timeout)
            await element.evaluate(
                """
                (el, value) => {
                  el.focus();
                  // For contenteditable, set innerText; for others, set textContent/value
                  if (el.isContentEditable || el.getAttribute('contenteditable') === 'true') {
                    el.innerText = value;
                  } else if ('value' in el) {
                    el.value = value;
                  } else {
                    el.textContent = value;
                  }
                  const inputEvent = new InputEvent('input', { bubbles: true, cancelable: true, data: value, inputType: 'insertText' });
                  el.dispatchEvent(inputEvent);
                  const changeEvent = new Event('change', { bubbles: true });
                  el.dispatchEvent(changeEvent);
                }
                """,
                text,
            )

            if submit:
                try:
                    await element.press("Enter")
                except Exception:
                    pass

            return ToolResult(
                success=True,
                content=f'Typed "{text}" into {selector} using JS fallback{ " and submitted" if submit else ""}',
                data={"selector": selector, "text": text, "fallback": "contenteditable"},
            ).to_string()
        except Exception as js_exc:
            return ToolResult(
                success=False,
                content=f"Error typing into element {selector}: {exc}; JS fallback failed: {js_exc}",
                data={"selector": selector},
            ).to_string()


@async_session_tool
async def browser_select_option(
    ref: str | None = None,
    selector: str | None = None,
    values: list[str] | None = None,
    timeout: int = 5000,
    page: Page = None,
) -> str:
    """Select one or more options from a dropdown select element.

    PREFERRED: Use ref from browser_get_snapshot for precise targeting.
    FALLBACK: Use selector if ref not available.
    """
    from src.tools.ref_registry import resolve_ref, get_snapshot

    if values is None:
        values = []

    # Try ref resolution first (preferred path)
    if ref:
        try:
            element = await resolve_ref(page, ref)

            # Get element info for response
            snapshot_data = get_snapshot(page)
            element_info = {}
            if snapshot_data and ref in snapshot_data.refs:
                element_ref = snapshot_data.refs[ref]
                element_info = {
                    "ref": ref,
                    "role": element_ref.role,
                    "name": element_ref.name
                }

            await element.select_option(values)

            content = f"Selected {len(values)} option(s) from {element_info.get('role', 'element')}"
            if element_info.get("name"):
                content += f" '{element_info['name']}'"
            content += f" [ref={ref}]: {', '.join(values)}"

            return ToolResult(
                success=True,
                content=content,
                data={"ref": ref, "values": values, "element": element_info},
            ).to_string()

        except ValueError as e:
            # If selector provided, fall through to selector-based selection
            if selector:
                pass  # Continue to selector fallback
            else:
                return ToolResult(
                    success=False,
                    content=f"Ref resolution failed: {e}",
                    data={"ref": ref},
                ).to_string()

    # Selector-based selection (fallback)
    if not selector:
        return ToolResult(
            success=False,
            content="Either 'ref' or 'selector' must be provided",
        ).to_string()

    try:
        element = _get_locator(page, selector)
        await element.wait_for(state="visible", timeout=timeout)
        await element.select_option(values)

        return ToolResult(
            success=True,
            content=f"Selected {len(values)} option(s) from {selector}: {', '.join(values)}",
            data={"selector": selector, "values": values},
        ).to_string()
    except Exception as exc:
        return ToolResult(
            success=False,
            content=f"Error selecting options from {selector}: {exc}",
            data={"selector": selector, "values": values},
        ).to_string()


@async_session_tool
async def browser_hover(
    ref: str | None = None,
    selector: str | None = None,
    timeout: int = 5000,
    page: Page = None,
) -> str:
    """Hover the mouse over an element.

    PREFERRED: Use ref from browser_get_snapshot for precise targeting.
    FALLBACK: Use selector if ref not available.
    """
    from src.tools.ref_registry import resolve_ref, get_snapshot

    # Try ref resolution first (preferred path)
    if ref:
        try:
            element = await resolve_ref(page, ref)

            # Get element info for response
            snapshot_data = get_snapshot(page)
            element_info = {}
            if snapshot_data and ref in snapshot_data.refs:
                element_ref = snapshot_data.refs[ref]
                element_info = {
                    "ref": ref,
                    "role": element_ref.role,
                    "name": element_ref.name
                }

            await element.hover()

            content = f"Hovered over {element_info.get('role', 'element')}"
            if element_info.get("name"):
                content += f" '{element_info['name']}'"
            content += f" [ref={ref}]"

            return ToolResult(
                success=True,
                content=content,
                data={"ref": ref, "element": element_info},
            ).to_string()

        except ValueError as e:
            # If selector provided, fall through to selector-based hover
            if selector:
                pass  # Continue to selector fallback
            else:
                return ToolResult(
                    success=False,
                    content=f"Ref resolution failed: {e}",
                    data={"ref": ref},
                ).to_string()

    # Selector-based hover (fallback)
    if not selector:
        return ToolResult(
            success=False,
            content="Either 'ref' or 'selector' must be provided",
        ).to_string()

    try:
        element = _get_locator(page, selector)
        await element.wait_for(state="visible", timeout=timeout)
        await element.hover()

        return ToolResult(
            success=True,
            content=f"Hovered over element: {selector}",
            data={"selector": selector},
        ).to_string()
    except Exception as exc:
        return ToolResult(
            success=False,
            content=f"Error hovering over {selector}: {exc}",
            data={"selector": selector},
        ).to_string()


@async_session_tool
async def browser_press_key(
    key: str,
    modifiers: list[str] = None,
    delay: int = 0,
    page: Page = None,
) -> str:
    """Press a keyboard key or key combination."""
    if modifiers is None:
        modifiers = []

    try:
        await page.keyboard.press(key, modifiers=modifiers)

        if delay > 0:
            await page.wait_for_timeout(delay)

        modifier_prefix = "+".join(modifiers)
        pressed = f"{modifier_prefix}+{key}" if modifier_prefix else key

        return ToolResult(
            success=True,
            content=f"Pressed key: {pressed}",
            data={"key": key, "modifiers": modifiers, "delay": delay},
        ).to_string()
    except Exception as exc:
        # Fallback: dispatch keyboard events on the active element via JS
        try:
            await page.evaluate(
                """
                (k) => {
                  const active = document.activeElement || document.body;
                  const opts = { key: k, code: k, keyCode: k === 'Enter' ? 13 : undefined, which: k === 'Enter' ? 13 : undefined, bubbles: true, cancelable: true };
                  ['keydown','keypress','keyup'].forEach(type => {
                    const evt = new KeyboardEvent(type, opts);
                    active.dispatchEvent(evt);
                  });
                }
                """,
                key,
            )

            modifier_prefix = "+".join(modifiers)
            pressed = f"{modifier_prefix}+{key}" if modifier_prefix else key

            return ToolResult(
                success=True,
                content=f"Pressed key via JS fallback: {pressed}",
                data={"key": key, "modifiers": modifiers, "fallback": "js"},
            ).to_string()
        except Exception as js_exc:
            return ToolResult(
                success=False,
                content=f"Error pressing key {key}: {exc}; JS fallback failed: {js_exc}",
                data={"key": key, "modifiers": modifiers},
            ).to_string()
