"""Element reference registry for ref-based targeting.

Tracks elements from accessibility snapshots and resolves refs to locators.
Based on Microsoft Playwright MCP patterns.
"""

import json
import os
import time
import weakref
from dataclasses import dataclass
from typing import Any, Literal

from playwright.async_api import Page, Locator


# ============= Configuration =============

DEBUG_REFS = os.getenv("DEBUG_REFS", "false").lower() == "true"

# Per-page ref storage (auto-cleanup when page closes)
_ref_registries: "weakref.WeakKeyDictionary[Page, dict[str, Any]]" = weakref.WeakKeyDictionary()

# Performance timing tracking
_ref_timing: dict[str, list[float]] = {}


# ============= Data Structures =============


@dataclass
class ElementRef:
    """Reference to an element in the accessibility tree."""
    ref: str                    # e.g., "e42" or "0.3.1"
    role: str | None            # button, textbox, link, etc.
    name: str | None            # accessible name
    parent_ref: str | None      # Parent element ref
    sibling_index: int          # Position among siblings
    attributes: dict[str, str]  # aria-label, id, data-testid, etc.


@dataclass
class SnapshotData:
    """Structured snapshot data with element mapping."""
    refs: dict[str, ElementRef]  # ref -> ElementRef
    root_ref: str | None         # Top-level element ref
    timestamp: float             # When snapshot was taken


# ============= Registry Functions =============


def get_registry(page: Page) -> dict[str, Any]:
    """Get or create ref registry for a page."""
    if page not in _ref_registries:
        _ref_registries[page] = {}
    return _ref_registries[page]


def store_snapshot(page: Page, data: SnapshotData) -> None:
    """Store snapshot ref data for a page."""
    registry = get_registry(page)
    registry["snapshot"] = data


def get_snapshot(page: Page) -> SnapshotData | None:
    """Get current snapshot data for a page."""
    registry = get_registry(page)
    return registry.get("snapshot")


def clear_registry(page: Page) -> None:
    """Clear refs for a page (call on navigation)."""
    _ref_registries.pop(page, None)


def should_refresh_snapshot(snapshot_data: SnapshotData | None) -> bool:
    """Check if snapshot should be refreshed.

    Returns True if:
    - No snapshot exists
    - Snapshot is older than 30 seconds
    - Snapshot has no refs (empty)
    """
    if not snapshot_data:
        return True

    age = time.time() - snapshot_data.timestamp
    if age > 30:
        return True

    if not snapshot_data.refs:
        return True

    return False


def get_refresh_suggestion() -> str:
    """Return suggestion to refresh snapshot."""
    return "Call browser_get_snapshot to refresh element refs"


# ============= Debug Logging =============


def log_ref_op(operation: str, details: dict) -> None:
    """Log ref operations for debugging."""
    if not DEBUG_REFS:
        return
    print(f"[REF_DEBUG] {operation}: {json.dumps(details)}")


def time_ref_op(operation: str, duration: float) -> None:
    """Track ref operation timing."""
    if operation not in _ref_timing:
        _ref_timing[operation] = []
    _ref_timing[operation].append(duration)

    # Keep only last 100
    if len(_ref_timing[operation]) > 100:
        _ref_timing[operation] = _ref_timing[operation][-100:]


# ============= Ref Generation =============


def _build_snapshot_yaml(node: dict, refs: dict[str, ElementRef], indent: int = 0, ref_lookup: dict | None = None) -> str:
    """Build human-readable YAML snapshot from accessibility tree.

    Args:
        node: Accessibility tree node
        refs: Dict mapping ref strings to ElementRef objects
        indent: Current indentation level
        ref_lookup: Optional pre-built index for O(1) ref lookup
    """
    prefix = "  " * indent
    lines = []

    role = node.get("role", "")
    name = node.get("name", "")

    # Build element line
    if role:
        line = f"- {role}"
        if name:
            line += f" '{name}'"

        # Add ref if this element has one - use index for O(1) lookup
        if ref_lookup:
            # Build composite key for matching (role+name+sibling position for uniqueness)
            # But for simplicity, just use role+name with the pre-built index
            key = (role, name)
            if key in ref_lookup:
                # Get the first ref for this role+name combo
                ref_str = ref_lookup[key][0]
                line += f" [ref={ref_str}]"

        lines.append(line)

    # Recurse into children
    for child in node.get("children", []):
        lines.append(_build_snapshot_yaml(child, refs, indent + 1, ref_lookup))

    return "\n".join(lines)


async def generate_refs(page: Page, root: str = "body") -> tuple[str, SnapshotData]:
    """Generate refs from accessibility snapshot.

    Uses Playwright's locator.aria_snapshot() API (Playwright 1.49+).

    Returns:
        (human_readable_snapshot, structured_data)
    """
    import sys
    import re
    start_time = time.time()
    log_ref_op("generate_refs_start", {"root": root})

    # Get ARIA snapshot using new API (Playwright 1.49+)
    try:
        locator = page.locator(root).first
        aria_text = await locator.aria_snapshot(timeout=10000)
        print(f"[REFS] aria_snapshot length: {len(aria_text)}", file=sys.stderr)
    except Exception as e:
        print(f"[REFS] aria_snapshot failed: {e}", file=sys.stderr)
        empty_data = SnapshotData(
            refs={},
            root_ref=None,
            timestamp=time.time()
        )
        return f"Page snapshot failed: {e}", empty_data

    if not aria_text or aria_text.strip() == "":
        print("[REFS] Empty ARIA snapshot!", file=sys.stderr)
        empty_data = SnapshotData(
            refs={},
            root_ref=None,
            timestamp=time.time()
        )
        return "Page snapshot: (empty)", empty_data

    # Parse ARIA snapshot text and assign refs
    # Format: "- role \"name\"" or "- role \"name\":" with children indented
    refs: dict[str, ElementRef] = {}
    ref_counter = 0
    lines = aria_text.split('\n')
    ref_lines = []
    
    # Stack to track hierarchy: [(indent_level, ref)]
    # We use -1 indent for virtual root
    stack = [(-1, "root")]
    # Track sibling counts: {(parent_ref, role, name): count}
    sibling_counts = {}

    for line in lines:
        if not line.strip():
            continue

        # Match pattern: "- role" or "- role \"name\""
        match = re.match(r'^(\s*)-\s+(\w+)(?:\s+"([^"]*)")?', line)
        if match:
            indent = len(match.group(1))
            role = match.group(2)
            name = match.group(3) or ""

            # Manage stack to find parent
            while len(stack) > 1 and stack[-1][0] >= indent:
                stack.pop()
            
            parent_ref = stack[-1][1]
            
            # Calculate sibling index
            # Key distinguishes unique element types within the same parent
            sibling_key = (parent_ref, role, name)
            current_index = sibling_counts.get(sibling_key, 0)
            sibling_counts[sibling_key] = current_index + 1

            ref = f"e{ref_counter}"
            ref_counter += 1
            
            # Push self to stack for potential children
            stack.append((indent, ref))

            # Store element ref
            element_ref = ElementRef(
                ref=ref,
                role=role,
                name=name,
                parent_ref=parent_ref if parent_ref != "root" else None,
                sibling_index=current_index,
                attributes={}
            )
            refs[ref] = element_ref

            # Add ref annotation to line
            ref_line = line.rstrip()
            if name:
                ref_line += f" [ref={ref}]"
            else:
                # Insert ref after role
                ref_line = re.sub(r'^(\s*-\s+\w+)', rf'\1 [ref={ref}]', line.rstrip())
            ref_lines.append(ref_line)
        else:
            ref_lines.append(line.rstrip())

    snapshot_yaml = '\n'.join(ref_lines)

    duration = time.time() - start_time
    time_ref_op("generate_refs", duration)
    log_ref_op("generate_refs_complete", {
        "ref_count": len(refs),
        "duration_ms": round(duration * 1000, 2)
    })

    print(f"[REFS] Generated {len(refs)} refs in {duration*1000:.1f}ms", file=sys.stderr)

    return snapshot_yaml, SnapshotData(
        refs=refs,
        root_ref=list(refs.keys())[0] if refs else None,
        timestamp=time.time()
    )


# ============= Ref Resolution =============


def _build_locator_for_ref(
    page: Page,
    element_ref: ElementRef,
    snapshot_data: SnapshotData
) -> Locator:
    """Build a Playwright locator for an element ref.

    Strategy priority:
    1. Strong attributes (id, data-testid)
    2. aria-label
    3. Role + exact name + sibling index
    4. Role + nth within parent
    """
    log_ref_op("build_locator", {
        "ref": element_ref.ref,
        "role": element_ref.role,
        "name": element_ref.name
    })

    # Strategy 1: Strong attributes (most stable)
    if "id" in element_ref.attributes:
        locator = page.locator(f"#{element_ref.attributes['id']}")
        log_ref_op("locator_strategy", {"ref": element_ref.ref, "strategy": "id"})
        return locator

    if "data-testid" in element_ref.attributes:
        locator = page.locator(f"[data-testid='{element_ref.attributes['data-testid']}']")
        log_ref_op("locator_strategy", {"ref": element_ref.ref, "strategy": "data-testid"})
        return locator

    # Strategy 2: aria-label (often stable)
    if "aria-label" in element_ref.attributes:
        locator = page.get_by_label(element_ref.attributes["aria-label"])
        log_ref_op("locator_strategy", {"ref": element_ref.ref, "strategy": "aria-label"})
        return locator

    # Strategy 3: Role + name (primary method)
    if element_ref.role and element_ref.name:
        locator = page.get_by_role(element_ref.role, name=element_ref.name, exact=True)

        # Apply sibling index
        locator = locator.nth(element_ref.sibling_index)

        log_ref_op("locator_strategy", {
            "ref": element_ref.ref,
            "strategy": "role+name",
            "role": element_ref.role,
            "name": element_ref.name,
            "nth": element_ref.sibling_index
        })
        return locator

    # Fallback: Less precise locator
    if element_ref.role:
        locator = page.get_by_role(element_ref.role).nth(element_ref.sibling_index)
        log_ref_op("locator_strategy", {
            "ref": element_ref.ref,
            "strategy": "role_only",
            "role": element_ref.role,
            "nth": element_ref.sibling_index
        })
        return locator

    raise ValueError(f"Cannot build locator for ref '{element_ref.ref}': insufficient data")


async def resolve_ref(page: Page, ref: str) -> Locator:
    """Resolve a ref to a Playwright locator.

    Args:
        page: Playwright page
        ref: Element reference (e.g., "e42")

    Returns:
        Playwright Locator for the element

    Raises:
        ValueError: If ref not found or stale
    """
    start_time = time.time()
    log_ref_op("resolve_ref_start", {"ref": ref})

    snapshot_data = get_snapshot(page)
    if not snapshot_data:
        raise ValueError(
            f"No snapshot data available. Call browser_get_snapshot first."
        )

    element_ref = snapshot_data.refs.get(ref)
    if not element_ref:
        # List available refs for debugging
        available = list(snapshot_data.refs.keys())[:10]
        log_ref_op("resolve_ref_not_found", {"ref": ref, "available": available})
        raise ValueError(
            f"Ref '{ref}' not found. Available refs: {available}..."
        )

    # Build locator strategy
    locator = _build_locator_for_ref(page, element_ref, snapshot_data)

    # Verify element exists (raises if stale)
    try:
        await locator.wait_for(state="attached", timeout=2000)
        duration = time.time() - start_time
        time_ref_op("resolve_ref", duration)
        log_ref_op("resolve_ref_success", {
            "ref": ref,
            "duration_ms": round(duration * 1000, 2)
        })

        if duration > 0.5:  # Slow resolution
            log_ref_op("slow_resolve", {"ref": ref, "duration": duration})

        return locator
    except Exception as e:
        log_ref_op("resolve_ref_stale", {"ref": ref, "error": str(e)})
        raise ValueError(
            f"Ref '{ref}' points to stale element. "
            f"{get_refresh_suggestion()}."
        ) from e


async def validate_ref(page: Page, ref: str) -> dict[str, Any]:
    """Validate ref without throwing.

    Returns validation result with status and info.
    """
    log_ref_op("validate_ref", {"ref": ref})

    result = {
        "valid": False,
        "ref": ref,
        "error": None,
        "element": None,
        "age_seconds": None
    }

    snapshot_data = get_snapshot(page)

    if not snapshot_data:
        result["error"] = "no_snapshot"
        return result

    result["age_seconds"] = time.time() - snapshot_data.timestamp

    element_ref = snapshot_data.refs.get(ref)
    if not element_ref:
        result["error"] = "ref_not_found"
        return result

    # Try to locate element
    try:
        locator = _build_locator_for_ref(page, element_ref, snapshot_data)
        count = await locator.count()
        if count == 0:
            result["error"] = "stale_element"
        else:
            result["valid"] = True
            result["element"] = {
                "ref": ref,
                "role": element_ref.role,
                "name": element_ref.name
            }
    except Exception as e:
        result["error"] = str(e)

    return result
