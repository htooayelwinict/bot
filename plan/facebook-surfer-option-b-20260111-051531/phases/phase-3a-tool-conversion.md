# Phase 3a: Tool Conversion

**Objective:** Convert remaining 17 tools from TypeScript to Python (interaction, forms, utilities, browser)

---

## Prerequisites

- Phase 1 complete (session + 5 core tools)
- Phase 2 complete (vision integration)
- Base tool patterns established

---

## Tasks

### 3a.1 Convert Interaction Tools (4 tools)

Convert from `src/mcp-tools/tools/interaction.ts`:

- [ ] `browser_type` - Type text into input fields with clearing
- [ ] `browser_select_option` - Dropdown selection by value/label
- [ ] `browser_hover` - Hover over elements
- [ ] `browser_press_key` - Keyboard input (Enter, Escape, etc.)

**Files:**
- `src/tools/interaction.py` - Add to existing click tool

**Conversion Pattern:**
```python
# src/tools/interaction.py
from pydantic import BaseModel, Field
from langchain.tools import tool
from typing import Literal

class TypeArgs(BaseModel):
    selector: str = Field(description="CSS selector for input element")
    text: str = Field(description="Text to type")
    clear: bool = Field(default=True, description="Clear field before typing")
    delay: int = Field(default=100, ge=0, le=1000, description="Delay before typing (ms)")
    timeout: int = Field(default=5000, ge=0, le=60000)

@tool
def browser_type(args: TypeArgs) -> str:
    """Type text into an input field. Optionally clears field before typing."""
    from src.tools.base import get_current_page
    page = get_current_page()

    locator = page.locator(args.selector).first
    locator.wait_for(timeout=args.timeout)

    if args.clear:
        locator.fill("")
        import time
        time.sleep(args.delay / 1000)

    locator.fill(args.text)
    return f"Typed '{args.text}' into {args.selector}"

class SelectOptionArgs(BaseModel):
    selector: str = Field(description="CSS selector for select element")
    value: str | None = Field(default=None, description="Option value to select")
    label: str | None = Field(default=None, description="Option label to select")
    timeout: int = Field(default=5000, ge=0, le=60000)

@tool
def browser_select_option(args: SelectOptionArgs) -> str:
    """Select an option from a dropdown by value or label."""
    from src.tools.base import get_current_page
    page = get_current_page()

    locator = page.locator(args.selector).first
    locator.wait_for(timeout=args.timeout)

    if args.value:
        locator.select_option(value=args.value)
        return f"Selected value '{args.value}'"
    else:
        locator.select_option(label=args.label)
        return f"Selected label '{args.label}'"

class HoverArgs(BaseModel):
    selector: str = Field(description="CSS selector for element")
    timeout: int = Field(default=5000, ge=0, le=60000)

@tool
def browser_hover(args: HoverArgs) -> str:
    """Hover over an element."""
    from src.tools.base import get_current_page
    page = get_current_page()

    locator = page.locator(args.selector).first
    locator.wait_for(timeout=args.timeout)
    locator.hover()
    return f"Hovered over {args.selector}"

class PressKeyArgs(BaseModel):
    key: str = Field(description="Key to press (Enter, Escape, ArrowDown, etc.)")
    modifiers: list[Literal["Shift", "Control", "Alt", "Meta"]] = Field(default=[])

@tool
def browser_press_key(args: PressKeyArgs) -> str:
    """Press a keyboard key with optional modifiers."""
    from src.tools.base import get_current_page
    from playwright.sync_api import Keyboard
    page = get_current_page()

    key_combo = "+".join(args.modifiers + [args.key])
    page.keyboard.press(key_combo)
    return f"Pressed {key_combo}"
```

### 3a.2 Convert Form Tools (3 tools)

Convert from `src/mcp-tools/tools/forms.ts`:

- [ ] `browser_fill_form` - Fill multiple fields at once
- [ ] `browser_get_form_data` - Extract form data
- [ ] `browser_submit_form` - Submit form

**Files:**
- `src/tools/forms.py` - Create new file

**Conversion Pattern:**
```python
# src/tools/forms.py
from pydantic import BaseModel, Field
from langchain.tools import tool
from typing import Literal

class FormField(BaseModel):
    name: str = Field(description="Field name or selector")
    type: Literal["textbox", "checkbox", "radio", "select"] = Field(description="Field type")
    value: str | bool = Field(description="Value to fill")

class FillFormArgs(BaseModel):
    fields: list[FormField] = Field(description="Array of fields to fill")
    submit: bool = Field(default=False, description="Submit after filling")
    timeout: int = Field(default=5000, ge=0, le=60000)

@tool
def browser_fill_form(args: FillFormArgs) -> str:
    """Fill multiple form fields with provided values."""
    from src.tools.base import get_current_page
    page = get_current_page()
    results = []

    for field in args.fields:
        locator = page.locator(f"[name=\"{field['name']}\"], #{field['name']}, [id=\"{field['name']}\"]").first
        locator.wait_for(timeout=args.timeout)

        if field['type'] == 'textbox':
            locator.fill(str(field['value']))
            results.append(f"Filled {field['name']}: {field['value']}")

        elif field['type'] == 'checkbox':
            if field['value']:
                locator.check()
            else:
                locator.uncheck()
            results.append(f"{'Checked' if field['value'] else 'Unchecked'} {field['name']}")

        elif field['type'] == 'select':
            locator.select_option(value=str(field['value']))
            results.append(f"Selected {field['name']}: {field['value']}")

    if args.submit:
        submit_btn = page.locator('button[type="submit"], input[type="submit"]').first
        submit_btn.click()
        results.append("Form submitted")

    return "\n".join(results)

class GetFormDataArgs(BaseModel):
    selector: str = Field(default="form", description="CSS selector for form")
    timeout: int = Field(default=5000, ge=0, le=60000)

@tool
def browser_get_form_data(args: GetFormDataArgs) -> str:
    """Extract data from form fields."""
    from src.tools.base import get_current_page
    import json
    page = get_current_page()

    form = page.locator(args.selector).first
    form.wait_for(timeout=args.timeout)

    # Get all inputs
    data = {}
    for input_type in ['input', 'textarea', 'select']:
        elements = form.locator(input_type).all()
        for el in elements:
            name = el.get_attribute('name')
            if name:
                if input_type == 'select':
                    data[name] = el.input_value()
                else:
                    input_type_attr = el.get_attribute('type')
                    if input_type_attr in ['checkbox', 'radio']:
                        data[name] = el.is_checked()
                    else:
                        data[name] = el.input_value()

    return json.dumps(data, indent=2)

class SubmitFormArgs(BaseModel):
    selector: str = Field(default="form", description="CSS selector for form")
    timeout: int = Field(default=5000, ge=0, le=60000)

@tool
def browser_submit_form(args: SubmitFormArgs) -> str:
    """Submit a form by clicking submit button."""
    from src.tools.base import get_current_page
    page = get_current_page()

    form = page.locator(args.selector).first
    form.wait_for(timeout=args.timeout)

    submit_btn = form.locator('button[type="submit"], input[type="submit"]').first
    submit_btn.click()

    return f"Submitted form: {args.selector}"
```

### 3a.3 Convert Utility Tools (5 tools)

Convert from `src/mcp-tools/tools/utilities.ts`:

- [ ] `browser_wait` - Wait for conditions
- [ ] `browser_evaluate` - Execute JavaScript
- [ ] `browser_get_snapshot` - Accessibility tree
- [ ] `browser_get_network_requests` - Network log
- [ ] `browser_get_console_messages` - Console log

**Files:**
- `src/tools/utilities.py` - Create new file

**Conversion Pattern:**
```python
# src/tools/utilities.py
from pydantic import BaseModel, Field
from langchain.tools import tool
from typing import Literal

class WaitArgs(BaseModel):
    condition: Literal["selector", "navigation", "time"] = Field(description="What to wait for")
    selector: str | None = Field(default=None, description="CSS selector (if condition=selector)")
    timeout: int = Field(default=30000, ge=0, le=120000, description="Max wait time (ms)")
    state: Literal["attached", "detached", "visible", "hidden"] = Field(default="visible")

@tool
def browser_wait(args: WaitArgs) -> str:
    """Wait for a condition to be met (selector, navigation, or time)."""
    from src.tools.base import get_current_page
    page = get_current_page()

    if args.condition == "selector" and args.selector:
        locator = page.locator(args.selector).first
        locator.wait_for(timeout=args.timeout, state=args.state)
        return f"Waited for selector {args.selector} to be {args.state}"
    elif args.condition == "navigation":
        page.wait_for_load_state("networkidle", timeout=args.timeout)
        return "Waited for navigation to complete"
    elif args.condition == "time":
        import time
        time.sleep(args.timeout / 1000)
        return f"Waited {args.timeout}ms"

class EvaluateArgs(BaseModel):
    expression: str = Field(description="JavaScript expression to evaluate")
    await_result: bool = Field(default=False, description="Await Promise result")

@tool
def browser_evaluate(args: EvaluateArgs) -> str:
    """Execute JavaScript in the page context."""
    from src.tools.base import get_current_page
    import json
    page = get_current_page()

    if args.await_result:
        result = page.evaluate(f"async () => {{ return {args.expression} }}")
    else:
        result = page.evaluate(args.expression)

    return json.dumps(result, default=str)

class GetSnapshotArgs(BaseModel):
    timeout: int = Field(default=5000, ge=0, le=60000)

@tool
def browser_get_snapshot(args: GetSnapshotArgs) -> str:
    """Get accessibility tree snapshot of the page."""
    from src.tools.base import get_current_page
    import json
    page = get_current_page()

    snapshot = page.accessibility.snapshot()
    return json.dumps(snapshot, indent=2)

class GetNetworkRequestsArgs(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)

@tool
def browser_get_network_requests(args: GetNetworkRequests) -> str:
    """Get recent network requests."""
    from src.tools.base import get_current_page
    import json
    page = get_current_page()

    # Requires enabling network monitoring in session setup
    requests = []
    # Implementation depends on session context
    return json.dumps(requests[-args.limit:], indent=2)

class GetConsoleMessagesArgs(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)

@tool
def browser_get_console_messages(args: GetConsoleMessagesArgs) -> str:
    """Get recent console messages."""
    from src.tools.base import get_current_page
    import json
    page = get_current_page()

    # Requires enabling console monitoring in session setup
    messages = []
    # Implementation depends on session context
    return json.dumps(messages[-args.limit:], indent=2)
```

### 3a.4 Convert Browser Tools (5 tools)

Convert from `src/mcp-tools/tools/browser.ts`:

- [ ] `browser_tabs` - Tab management (open, close, switch)
- [ ] `browser_resize` - Window resize
- [ ] `browser_handle_dialog` - Alert/confirm handling
- [ ] `browser_reload` - Page reload
- [ ] `browser_close` - Close browser/page

**Files:**
- `src/tools/browser.py` - Create new file

**Conversion Pattern:**
```python
# src/tools/browser.py
from pydantic import BaseModel, Field
from langchain.tools import tool
from typing import Literal

class TabsArgs(BaseModel):
    action: Literal["open", "close", "switch", "list"] = Field(description="Tab action")
    url: str | None = Field(default=None, description="URL for new tab")
    index: int | None = Field(default=None, description="Tab index to switch/close")

@tool
def browser_tabs(args: TabsArgs) -> str:
    """Manage browser tabs (open, close, switch, list)."""
    from src.tools.base import get_current_page, get_current_context
    context = get_current_context()
    page = get_current_page()

    if args.action == "open":
        if not args.url:
            return "Error: URL required for opening new tab"
        new_page = context.new_page()
        new_page.goto(args.url)
        return f"Opened new tab: {args.url}"

    elif args.action == "close":
        if args.index is not None:
            pages = context.pages
            if 0 <= args.index < len(pages):
                pages[args.index].close()
                return f"Closed tab at index {args.index}"
        return "Error: Invalid tab index"

    elif args.action == "switch":
        if args.index is not None:
            pages = context.pages
            if 0 <= args.index < len(pages):
                from src.tools.base import set_current_page
                set_current_page(pages[args.index])
                return f"Switched to tab {args.index}"
        return "Error: Invalid tab index"

    elif args.action == "list":
        pages = context.pages
        return "\n".join([f"{i}: {pages[i].url}" for i in range(len(pages))])

class ResizeArgs(BaseModel):
    width: int = Field(ge=320, le=3840, description="Viewport width")
    height: int = Field(ge=240, le=2160, description="Viewport height")

@tool
def browser_resize(args: ResizeArgs) -> str:
    """Resize browser viewport."""
    from src.tools.base import get_current_page
    page = get_current_page()

    page.set_viewport_size({"width": args.width, "height": args.height})
    return f"Resized to {args.width}x{args.height}"

class HandleDialogArgs(BaseModel):
    action: Literal["accept", "dismiss"] = Field(description="Dialog action")
    prompt_text: str | None = Field(default=None, description="Text for prompt dialog")

@tool
def browser_handle_dialog(args: HandleDialogArgs) -> str:
    """Handle alert/confirm/prompt dialogs."""
    from src.tools.base import get_current_page
    page = get_current_page()

    # Must set up dialog handler before action that triggers dialog
    def handle_dialog(dialog):
        if args.action == "accept":
            if args.prompt_text is not None:
                dialog.accept(args.prompt_text)
            else:
                dialog.accept()
        else:
            dialog.dismiss()

    page.on("dialog", handle_dialog)
    return f"Dialog handler registered: {args.action}"

class ReloadArgs(BaseModel):
    force: bool = Field(default=False, description="Force reload from server")

@tool
def browser_reload(args: ReloadArgs) -> str:
    """Reload current page."""
    from src.tools.base import get_current_page
    page = get_current_page()

    page.reload(wait_until="networkidle")
    return f"Reloaded page (force={args.force})"

class CloseArgs(BaseModel):
    target: Literal["page", "browser"] = Field(default="page")

@tool
def browser_close(args: CloseArgs) -> str:
    """Close page or browser."""
    from src.tools.base import get_current_page, get_current_context
    page = get_current_page()
    context = get_current_context()

    if args.target == "page":
        page.close()
        return "Closed current page"
    else:
        context.close()
        return "Closed browser context"
```

### 3a.5 Unit Tests

- [ ] Create comprehensive unit tests for all 17 tools
- [ ] Test error handling (timeouts, invalid selectors)
- [ ] Test edge cases (empty forms, no tabs, etc.)

**Files:**
- `tests/test_tools_conversion.py`

**Test Pattern:**
```python
# tests/test_tools_conversion.py
import pytest
from src.tools.interaction import browser_type, TypeArgs
from src.tools.forms import browser_fill_form, FillFormArgs
from src.tools.utilities import browser_wait, WaitArgs
from src.tools.browser import browser_tabs, TabsArgs

@pytest.mark.parametrize("tool_class,tool_args", [
    (browser_type, TypeArgs(selector="#test-input", text="hello")),
    (browser_fill_form, FillFormArgs(fields=[])),
    (browser_wait, WaitArgs(condition="time", timeout=1000)),
    (browser_tabs, TabsArgs(action="list")),
])
def test_tool_signature(tool_class, tool_args):
    """Test tools have correct signatures and can be called."""
    result = tool_class.invoke(tool_args)
    assert result is not None

def test_interaction_tools():
    """Test all interaction tools."""
    # Test browser_type, browser_select_option, browser_hover, browser_press_key
    pass

def test_form_tools():
    """Test all form tools."""
    # Test browser_fill_form, browser_get_form_data, browser_submit_form
    pass

def test_utility_tools():
    """Test all utility tools."""
    # Test browser_wait, browser_evaluate, browser_get_snapshot
    pass

def test_browser_tools():
    """Test all browser tools."""
    # Test browser_tabs, browser_resize, browser_handle_dialog
    pass
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `src/tools/interaction.py` | Type, select, hover, press_key |
| `src/tools/forms.py` | Fill, get_data, submit |
| `src/tools/utilities.py` | Wait, evaluate, snapshot, network, console |
| `src/tools/browser.py` | Tabs, resize, dialog, reload, close |
| `tests/test_tools_conversion.py` | Unit tests for all 17 tools |

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/tools/__init__.py` | Export all new tools |
| `pyproject.toml` | No changes needed (dependencies already in Phase 1) |

---

## Verification

```bash
# 1. Test each tool category
pytest tests/test_tools_conversion.py -v -k "test_interaction"
pytest tests/test_tools_conversion.py -v -k "test_forms"
pytest tests/test_tools_conversion.py -v -k "test_utilities"
pytest tests/test_tools_conversion.py -v -k "test_browser"

# 2. Verify all tools import
python -c "
from src.tools.interaction import browser_type, browser_select_option, browser_hover, browser_press_key
from src.tools.forms import browser_fill_form, browser_get_form_data, browser_submit_form
from src.tools.utilities import browser_wait, browser_evaluate, browser_get_snapshot, browser_get_network_requests, browser_get_console_messages
from src.tools.browser import browser_tabs, browser_resize, browser_handle_dialog, browser_reload, browser_close
print('All 17 tools imported successfully')
print('Interaction: 4 tools')
print('Forms: 3 tools')
print('Utilities: 5 tools')
print('Browser: 5 tools')
"

# 3. Run full test suite
pytest tests/test_tools_conversion.py -v --cov=src/tools
```

**Expected Results:**
- All 17 tools import without errors
- Unit tests pass for all tool categories
- Tool signatures match TypeScript originals
- Error handling works (timeouts, invalid inputs)

---

## Estimated Effort

**4-6 hours**

- Interaction tools: 1 hour
- Form tools: 1 hour
- Utility tools: 1.5 hours
- Browser tools: 1 hour
- Unit tests: 1.5 hours

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Locator strategy differences | Reference TS tool implementations |
| Async/sync differences | Use Playwright sync API consistently |
| Type hints complex | Use Pydantic for validation |
| Session context access | Use base.py helper functions |

---

## Dependencies

- Phase 1: Foundation (required) - base tool patterns
- Phase 2: Vision Integration (optional) - vision not needed for these tools
- Phase 3b: Agent Assembly (next) - uses these converted tools

---

## Exit Criteria

- [ ] All 17 tools converted from TypeScript
- [ ] Unit tests pass for all tools
- [ ] Tools follow established patterns from Phase 1
- [ ] Error handling implemented
- [ ] Documentation comments added
