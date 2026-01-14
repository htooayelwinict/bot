"""Utility tools for browser automation.

Ported from src/mcp-tools/tools/utilities.ts
"""

import asyncio
import json
import re
import time
import weakref
from typing import Any, Literal, Optional

from playwright.async_api import Page
from pydantic import BaseModel, Field

from src.tools.base import ToolResult, async_session_tool

# ============= Tracking Types =============

MAX_TRACKED_ENTRIES = 2000

request_records: "weakref.WeakKeyDictionary[Page, list[dict]]" = weakref.WeakKeyDictionary()
console_records: "weakref.WeakKeyDictionary[Page, list[dict]]" = weakref.WeakKeyDictionary()

level_weights = {
    "debug": 0,
    "trace": 0,
    "log": 1,
    "info": 1,
    "warn": 2,
    "warning": 2,
    "error": 3,
}

severity_threshold = {
    "debug": 0,
    "info": 1,
    "warning": 2,
    "error": 3,
}


def _trim_records(records: list[Any]) -> None:
    if len(records) > MAX_TRACKED_ENTRIES:
        del records[: len(records) - MAX_TRACKED_ENTRIES]


def _call_if_callable(value: Any) -> Any:
    return value() if callable(value) else value


def _record_request_entry(page: Page, entry: dict) -> None:
    store = request_records.get(page)
    if store is None:
        return
    store.append(entry)
    _trim_records(store)


def ensure_request_tracking(page: Page) -> None:
    if page in request_records:
        return

    request_records[page] = []

    def on_request_finished(request: Any) -> None:
        try:
            # Get response - handle both sync method and coroutine
            resp_method = getattr(request, "response", None)
            if resp_method and callable(resp_method):
                resp = resp_method()
                # If it returns a coroutine, skip detailed response tracking
                if asyncio.iscoroutine(resp):
                    response = None
                else:
                    response = resp
            else:
                response = None

            if response:
                headers = _call_if_callable(getattr(response, "headers", None)) or {}
                size_header = headers.get("content-length") if isinstance(headers, dict) else None
                size = int(size_header) if size_header and str(size_header).isdigit() else None
            else:
                size = None

            _record_request_entry(
                page,
                {
                    "url": _call_if_callable(request.url),
                    "method": _call_if_callable(request.method),
                    "status": _call_if_callable(getattr(response, "status", None)) if response else None,
                    "resource_type": _call_if_callable(request.resource_type),
                    "size": size,
                    "timestamp": int(time.time() * 1000),
                },
            )
        except Exception:
            _record_request_entry(
                page,
                {
                    "url": _call_if_callable(request.url),
                    "method": _call_if_callable(request.method),
                    "resource_type": _call_if_callable(request.resource_type),
                    "timestamp": int(time.time() * 1000),
                },
            )

    def on_request_failed(request: Any) -> None:
        failure = _call_if_callable(getattr(request, "failure", None))
        failure_text = None
        if isinstance(failure, dict):
            failure_text = failure.get("errorText")
        else:
            failure_text = getattr(failure, "error_text", None) or getattr(failure, "errorText", None)

        _record_request_entry(
            page,
            {
                "url": _call_if_callable(request.url),
                "method": _call_if_callable(request.method),
                "resource_type": _call_if_callable(request.resource_type),
                "failure_text": failure_text,
                "timestamp": int(time.time() * 1000),
            },
        )

    page.on("requestfinished", on_request_finished)
    page.on("requestfailed", on_request_failed)
    page.once("close", lambda: request_records.pop(page, None))


def ensure_console_tracking(page: Page) -> None:
    if page in console_records:
        return

    console_records[page] = []

    def on_console_message(message: Any) -> None:
        message_type = _call_if_callable(getattr(message, "type", None)) or "log"
        weight = level_weights.get(message_type, 1)
        entry: dict = {
            "type": message_type,
            "text": _call_if_callable(getattr(message, "text", None)) or "",
            "location": _call_if_callable(getattr(message, "location", None)),
            "timestamp": int(time.time() * 1000),
            "weight": weight,
        }

        args_handles = _call_if_callable(getattr(message, "args", None)) or []
        if args_handles:
            serialized_args: list[str] = []
            for handle in args_handles:
                try:
                    # Try json_value() method but handle async gracefully
                    json_val_method = getattr(handle, "json_value", None)
                    if json_val_method and callable(json_val_method):
                        result = json_val_method()
                        # If it returns a coroutine, skip serialization
                        if asyncio.iscoroutine(result):
                            serialized_args.append(f"<async_object>")
                        else:
                            serialized_args.append(result if isinstance(result, str) else json.dumps(result))
                    else:
                        serialized_args.append(str(handle))
                except Exception:
                    serialized_args.append(str(handle))
            entry["args"] = serialized_args

        store = console_records.get(page)
        if store is None:
            return
        store.append(entry)
        _trim_records(store)

    page.on("console", on_console_message)
    page.once("close", lambda: console_records.pop(page, None))


# ============= Tool Argument Schemas =============


class WaitArgs(BaseModel):
    """Arguments for browser_wait tool."""

    time: Optional[float] = Field(
        default=None,
        ge=0.1,
        le=300,
        description="Wait time in seconds (0.1 to 300)",
    )
    text: Optional[str] = Field(default=None, description="Text to wait for on the page")
    text_gone: Optional[str] = Field(default=None, description="Text to wait for to disappear")
    selector: Optional[str] = Field(default=None, description="CSS selector to wait for element")
    state: Literal["attached", "detached", "visible", "hidden"] = Field(
        default="visible",
        description="Element state to wait for",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Maximum wait time in seconds",
    )


class EvaluateArgs(BaseModel):
    """Arguments for browser_evaluate tool."""

    script: str = Field(description="JavaScript code to execute")
    wait_for_function: bool = Field(
        default=False,
        description="Whether to wait for the script to return a truthy value",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Maximum time to wait for function in seconds",
    )


class GetSnapshotArgs(BaseModel):
    """Arguments for browser_get_snapshot tool."""

    root: str = Field(
        default="body",
        description="CSS selector to limit snapshot to a specific subtree",
    )


class GetNetworkRequestsArgs(BaseModel):
    """Arguments for browser_get_network_requests tool."""

    include_static: bool = Field(
        default=False,
        description="Whether to include static resources (images, fonts, scripts)",
    )
    filter: Optional[str] = Field(
        default=None,
        description="Filter requests by URL pattern (regex)",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of requests to return",
    )


class GetConsoleMessagesArgs(BaseModel):
    """Arguments for browser_get_console_messages tool."""

    level: Literal["error", "warning", "info", "debug"] = Field(
        default="info",
        description="Minimum log level to retrieve",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of messages to retrieve",
    )


# ============= Tool Functions =============


@async_session_tool
async def browser_wait(
    time: Optional[float] = None,
    text: Optional[str] = None,
    text_gone: Optional[str] = None,
    selector: Optional[str] = None,
    state: str = "visible",
    timeout: int = 30,
    page: Page = None,
) -> str:
    """Wait for a specified time, text to appear/disappear, or element."""
    timeout_ms = timeout * 1000

    try:
        if time is not None:
            await page.wait_for_timeout(int(time * 1000))
            return ToolResult(
                success=True,
                content=f"Waited {time} second(s)",
                data={"time": time},
            ).to_string()

        if text:
            text_locator = page.get_by_text(text, exact=False).first
            await text_locator.wait_for(state="visible", timeout=timeout_ms)
            return ToolResult(
                success=True,
                content=f"Waited for text to appear: '{text}'",
                data={"text": text},
            ).to_string()

        if text_gone:
            text_locator = page.get_by_text(text_gone, exact=False).first
            await text_locator.wait_for(state="hidden", timeout=timeout_ms)
            return ToolResult(
                success=True,
                content=f"Waited for text to disappear: '{text_gone}'",
                data={"text_gone": text_gone},
            ).to_string()

        if selector:
            element = page.locator(selector).first
            await element.wait_for(state=state, timeout=timeout_ms)
            return ToolResult(
                success=True,
                content=f"Waited for element: {selector} (state: {state})",
                data={"selector": selector, "state": state},
            ).to_string()

        return ToolResult(
            success=False,
            content="No valid wait condition provided. Use time, text, text_gone, or selector.",
        ).to_string()
    except Exception as exc:
        return ToolResult(
            success=False,
            content=f"Wait failed: {exc}",
        ).to_string()


@async_session_tool
async def browser_evaluate(
    script: str,
    wait_for_function: bool = False,
    timeout: int = 30,
    page: Page = None,
) -> str:
    """Execute JavaScript code in the browser page context.
    
    Use this for:
    - Extracting data from the page (URLs, text, attributes)
    - Clicking elements when browser_click fails (bypasses overlay issues)
    - Complex DOM operations
    
    Click examples (when browser_click fails):
    - Click by aria-label: document.querySelector('[aria-label="Only me"]')?.click()
    - Click by text content: [...document.querySelectorAll('span')].find(el => el.textContent.includes('Only me'))?.click()
    - Click by role: document.querySelector('[role="radio"][aria-label*="Only me"]')?.click()
    
    Data extraction examples:
    - Get href: document.querySelector('a[aria-label="Profile"]')?.href
    - Get all links: Array.from(document.querySelectorAll('a')).map(a => ({text: a.textContent, href: a.href}))
    """
    timeout_ms = timeout * 1000

    def _wrap_script(user_script: str, for_wait: bool = False) -> str:
        """Allow full statements or raw functions instead of expression-only.

        - If the user already provided a function (e.g., "() => {...}"), use it verbatim.
        - If the script contains statements/semicolons, wrap in a function body.
        - Otherwise treat it as a simple expression.
        """
        trimmed = user_script.strip()

        # Pre-wrapped function provided by caller
        if trimmed.startswith(("() =>", "async () =>", "function", "async function")):
            return trimmed

        has_statements = any(token in trimmed for token in [";", "\n", "const ", "let ", "var "])

        if for_wait:
            # wait_for_function requires a function returning truthy value
            if has_statements:
                return f"() => {{ {trimmed} }}"
            return f"() => {{ return {trimmed} }}"

        # Standard evaluate: permit statements and optional return
        if has_statements:
            return f"() => {{ {trimmed} }}"
        return f"() => {trimmed}"

    try:
        if wait_for_function:
            wrapped = _wrap_script(script, for_wait=True)
            handle = await page.wait_for_function(wrapped, timeout=timeout_ms)
            result = await handle.json_value()
        else:
            wrapped = _wrap_script(script, for_wait=False)
            result = await page.evaluate(wrapped)

        result_text = (
            json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)
        )

        return ToolResult(
            success=True,
            content=f"JavaScript executed successfully.\nResult: {result_text}",
            data={"result": result},
        ).to_string()
    except Exception as exc:
        return ToolResult(
            success=False,
            content=f"JavaScript execution failed: {exc}",
        ).to_string()


@async_session_tool
async def browser_get_snapshot(root: str = "body", page: Page = None) -> str:
    """Get accessibility snapshot with element refs for precise targeting.

    Returns a YAML accessibility tree showing all interactable elements with their
    aria-labels, roles, text content, and unique refs. Use refs from this snapshot
    for unambiguous element targeting in click/type/hover tools.

    REF USAGE:
    - Each element has a ref like [ref=e42]
    - Use ref in tools: browser_click(ref="e42")
    - Refs are page-scoped (refresh after navigation/UI changes)

    Example workflow:
    1. Call browser_get_snapshot() to get refs
    2. Find target element's ref (e.g., button "Post" [ref=e42])
    3. Use browser_click(ref="e42") for precise targeting
    4. Refresh snapshot after UI changes
    """
    from src.tools.ref_registry import generate_refs, store_snapshot, should_refresh_snapshot
    import sys

    try:
        snapshot_yaml, snapshot_data = await generate_refs(page, root)
        store_snapshot(page, snapshot_data)

        print(f"[SNAPSHOT] Generated {len(snapshot_data.refs)} refs, yaml length={len(snapshot_yaml)}", file=sys.stderr)

        # Build ref summary for interactive elements only
        ref_list = [
            {"ref": r.ref, "role": r.role, "name": r.name}
            for r in snapshot_data.refs.values()
            if r.role and r.role not in ["generic", "text", "document", "section", "article"]
        ]

        print(f"[SNAPSHOT] Interactive elements: {len(ref_list)}", file=sys.stderr)

        # Check if snapshot should be refreshed
        age = time.time() - snapshot_data.timestamp
        refresh_hint = ""
        if age > 20:
            refresh_hint = f"\n\n💡 Snapshot is {age:.0f}s old. Refresh after UI changes."

        return ToolResult(
            success=True,
            content=f"Page snapshot:{refresh_hint}\n{snapshot_yaml}\n\nInteractive elements: {len(ref_list)}",
            data={
                "refs": ref_list,
                "ref_count": len(ref_list),
                "root_ref": snapshot_data.root_ref,
                "snapshot_age_seconds": round(age, 1)
            }
        ).to_string()
    except Exception as exc:
        import traceback
        print(f"[SNAPSHOT] Exception: {exc}", file=sys.stderr)
        traceback.print_exc()
        return ToolResult(
            success=False,
            content=f"Failed to get snapshot: {exc}",
        ).to_string()


@async_session_tool
async def browser_get_network_requests(
    include_static: bool = False,
    filter: Optional[str] = None,
    limit: int = 100,
    page: Page = None,
) -> str:
    """Get all network requests made since page load."""
    try:
        ensure_request_tracking(page)
        recorded = list(request_records.get(page, []))

        if not include_static:
            static_extensions = [
                ".css",
                ".js",
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".svg",
                ".ico",
                ".woff",
                ".woff2",
                ".ttf",
            ]
            filtered = []
            for req in recorded:
                url = req.get("url", "").lower()
                if not any(ext in url for ext in static_extensions):
                    filtered.append(req)
            recorded = filtered

        if filter:
            try:
                regex = re.compile(filter, re.IGNORECASE)
            except re.error:
                return ToolResult(
                    success=False,
                    content=f"Invalid filter regex: {filter}",
                ).to_string()
            recorded = [req for req in recorded if regex.search(req.get("url", ""))]

        limited = recorded[-limit:]
        summary = [
            {
                "url": req.get("url"),
                "method": req.get("method"),
                "status": req.get("status") or ("failed" if req.get("failure_text") else "pending"),
                "type": req.get("resource_type"),
                "size": req.get("size"),
                "failure": req.get("failure_text"),
                "timestamp": req.get("timestamp"),
            }
            for req in limited
        ]

        return ToolResult(
            success=True,
            content=f"Network requests ({len(summary)} total):\n{json.dumps(summary, indent=2)}",
            data={"requests": summary},
        ).to_string()
    except Exception as exc:
        return ToolResult(
            success=False,
            content=f"Failed to get network requests: {exc}",
        ).to_string()


@async_session_tool
async def browser_get_console_messages(
    level: str = "info",
    limit: int = 100,
    page: Page = None,
) -> str:
    """Get console messages from the browser."""
    try:
        ensure_console_tracking(page)
        severity = severity_threshold.get(level, 1)
        messages = [
            entry for entry in console_records.get(page, []) if entry.get("weight", 0) >= severity
        ]
        limited = messages[-limit:]

        summary = [
            {
                "type": msg.get("type"),
                "text": msg.get("text"),
                "location": msg.get("location"),
                "args": msg.get("args"),
                "timestamp": msg.get("timestamp"),
            }
            for msg in limited
        ]

        return ToolResult(
            success=True,
            content=(
                f"Console messages ({len(summary)} total, level >= {level}):\n"
                f"{json.dumps(summary, indent=2)}"
            ),
            data={"messages": summary},
        ).to_string()
    except Exception as exc:
        return ToolResult(
            success=False,
            content=f"Failed to get console messages: {exc}",
        ).to_string()
