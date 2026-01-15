---
name: facebook-automation
description: Facebook automation including posting with privacy settings, interactions, messaging, and navigation workflows
allowed-tools: browser_navigate browser_click browser_type browser_fill_form browser_get_snapshot browser_screenshot browser_wait browser_navigate_back browser_get_page_info browser_hover browser_press_key browser_evaluate browser_scroll
---

# Facebook Automation Skill

Automation guide for Facebook web interface - posts, privacy settings, interactions, and navigation.

## When to Use This Skill
- Create posts with specific privacy settings (Public, Friends, Only me)
- Navigate Facebook pages and features
- Interact with posts (like, comment, share)
- Send messages via Messenger

---

## Critical Rules

### ⚠️ REFS BECOME STALE AFTER EVERY ACTION

After ANY click, type, or navigation:
- **ALL refs from previous snapshot are INVALID**
- You MUST call `browser_get_snapshot()` to get fresh refs
- The same ref number (e.g., `e78`) now points to a DIFFERENT element

**Example of what goes wrong:**
```python
browser_get_snapshot()
# e78 = button "What's on your mind?"
browser_click(ref="e78", force=True)  # Opens dialog

browser_click(ref="e78", force=True)  # WRONG! e78 is now "Live video"!
```

**Correct pattern:**
```python
browser_get_snapshot()
# e78 = button "What's on your mind?"
browser_click(ref="e78", force=True)

browser_get_snapshot()  # GET FRESH REFS!
# Now e78 might be something completely different
# e42 = button "Friends" (privacy button)
browser_click(ref="e42", force=True)
```

### 1. ARIA Snapshot & Ref System

The `browser_get_snapshot()` tool returns a YAML accessibility tree using Playwright's `locator.aria_snapshot()` API:

```yaml
- navigation "Facebook":
  - link "Home" [ref=e0]
  - button "Search" [ref=e1]
- main:
  - button "What's on your mind?" [ref=e15]
  - dialog "Create post":
    - textbox "What's on your mind?" [ref=e20]
    - button "Public" [ref=e21]
    - button "Post" [ref=e25]
```

**Format explanation:**
- `role "accessible name" [ref=eN]` - Each element with unique ref
- Roles: `button`, `link`, `textbox`, `checkbox`, `radio`, `heading`, `dialog`, etc.
- Attributes: `[checked]`, `[disabled]`, `[expanded]`, `[pressed=true]`

### 2. Mandatory Workflow (Observe → Think → Act → Verify)

**BEFORE ANY ACTION:**

```python
# OBSERVE - Get FRESH snapshot
browser_get_snapshot()

# THINK - MUST explicitly list elements you see:
# I see in this snapshot:
# - button "Close composer dialog" [ref=e31] ← NOT what I want!
# - button "Friends" [ref=e42] ← This is the privacy button (shows current setting)
# - button "Photo/video" [ref=e43] ← NOT privacy
# - button "Post" [ref=e50] ← Submit button
#
# I need to change privacy. The button showing "Friends" is ref=e42.

# ACT - Use the ref from THIS snapshot
browser_click(ref="e42", force=True)

# VERIFY - Get NEW snapshot (previous refs are now stale!)
browser_wait(time=1)
browser_get_snapshot()  # REQUIRED after every action
# Now analyze the NEW refs before next action
```

### 3. Must-Follow Principles

| Rule | Why |
|------|-----|
| **Get fresh snapshot after EVERY action** | Refs become stale immediately |
| Always `force=True` on clicks | Facebook has invisible overlays |
| `browser_wait(time=1-2)` after actions | React needs time to re-render |
| **List elements before clicking** | Prevents clicking wrong button |
| Complete ALL dialog steps | Selecting ≠ confirming |
| Verify with snapshot before "done" | Task isn't complete until verified |
| **Read button names carefully** | "Close composer" ≠ privacy button! |

---

## Tool Reference

### browser_get_snapshot
Get ARIA accessibility snapshot with element refs.

```python
browser_get_snapshot()
```

**Output:** YAML accessibility tree with `[ref=eN]` markers on each element.

### browser_click
Click element using ref (preferred) or selector.

```python
# Using ref (RECOMMENDED)
browser_click(ref="e42", force=True)

# Using selector (fallback)
browser_click(selector="button=Post", force=True)
```

**Always use `force=True` on Facebook.**

### browser_type
Type text into an input field.

```python
# Using ref
browser_type(ref="e23", text="Hello world")

# Using selector
browser_type(selector="div[contenteditable='true'][role='textbox']", text="Hello")
```

### browser_wait
Wait for UI updates after actions.

```python
browser_wait(time=1)   # 1 second for simple actions
browser_wait(time=2)   # 2 seconds for navigation/dialogs
```

### browser_press_key
Press keyboard keys.

```python
browser_press_key(key="Enter")
browser_press_key(key="Escape")
```

### browser_hover
Hover to reveal hidden UI (like reactions).

```python
browser_hover(ref="e28")
```

---

## Selector Patterns

---

## Selector Patterns

**Priority order (most reliable first):**

1. `ref="e42"` - From snapshot (BEST)
2. `button=Name` - Buttons by accessible name
3. `radio=Option` - Radio buttons in dialogs
4. `[aria-label="Label"]` - By aria-label
5. `role=textbox` - For input fields
6. CSS selectors - Last resort

### Common Facebook Selectors

| Element | Selector |
|---------|----------|
| Open composer | `button=What's on your mind?` |
| Text input | `div[contenteditable='true'][role='textbox']` or `role=textbox` |
| Post button | `button=Post` |
| Next button | `button=Next` |
| Done button | `button=Done` |

### Privacy Selectors

**The privacy button shows CURRENT setting:**

| Current Privacy | Button Shows |
|-----------------|--------------|
| Public | `button=Public` |
| Friends | `button=Friends` |
| Only me | `button=Only me` |

**In privacy dialog:**

| Option | Selector |
|--------|----------|
| Public | `radio=Public` |
| Friends | `radio=Friends` |
| Only me | `radio=Only me` |
| Custom | `radio=Custom` |

---

## Core Workflows

### Create Post with Privacy Setting

```python
# 1. Navigate to Facebook
browser_navigate(url="https://www.facebook.com")
browser_wait(time=2)

# 2. Get snapshot to find composer
browser_get_snapshot()
# Find button containing "What's on your mind"

# 3. Open composer
browser_click(selector='button=What\'s on your mind', force=True)
browser_wait(time=1)

# 4. Get snapshot - find privacy button (shows current setting)
browser_get_snapshot()
# Look for button "Public" or "Friends" [ref=eXX]

# 5. Click privacy button (use ref from snapshot)
browser_click(ref="eXX", force=True)  # Replace with actual ref
browser_wait(time=0.5)

# 6. Select privacy option
browser_click(selector='radio=Only me', force=True)
browser_wait(time=0.5)

# 7. CRITICAL - Confirm with Done
browser_click(selector='button=Done', force=True)
browser_wait(time=0.5)

# 8. Type post content
browser_type(selector="role=textbox", text="Your post content")
browser_wait(time=1)

# 9. Click Next (if shown)
browser_click(selector='button=Next', force=True)
browser_wait(time=2)

# 10. Get snapshot, find Post button
browser_get_snapshot()

# 11. Click Post
browser_click(selector='button=Post', force=True)
browser_wait(time=3)

# 12. VERIFY - Must see post in feed
browser_get_snapshot()
```

### Like a Post

```python
browser_get_snapshot()
# Find Like button ref
browser_click(ref="e28", force=True)  # Like button ref
browser_wait(time=0.5)
browser_get_snapshot()  # Verify liked
```

### React with Emoji (Love, Haha, etc.)

```python
browser_get_snapshot()
# Hover to reveal reactions
browser_hover(ref="e28")  # Like button ref
browser_wait(time=1)
browser_get_snapshot()
# Click specific reaction
browser_click(ref="e35", force=True)  # Love reaction ref
```

### Comment on Post

```python
browser_get_snapshot()
browser_click(ref="e32", force=True)  # Comment button
browser_wait(time=0.5)
browser_type(ref="e45", text="Great post!")  # Comment input
browser_press_key(key="Enter")
browser_wait(time=1)
browser_get_snapshot()  # Verify comment appears
```

---

## Troubleshooting

### Common Failure Patterns

| Problem | What Happened | Fix |
|---------|---------------|-----|
| Clicked wrong button | Used stale ref (e78 was "What's on your mind" but became "Live video") | ALWAYS `browser_get_snapshot()` after any action |
| Closed dialog accidentally | Clicked "Close composer dialog" instead of privacy button | Read button names in snapshot before clicking |
| Got stuck in loop | Clicking same ref repeatedly after page changed | Refs are per-snapshot; get fresh snapshot first |
| Privacy not changed | Selected option but didn't click "Done" | Complete full dialog: select → Done → verify |

### Quick Fixes

| Problem | Solution |
|---------|----------|
| Ref not found | `browser_get_snapshot()` to refresh refs |
| Click not working | Add `force=True`, try `browser_hover` first |
| Element not visible | `browser_wait(time=2)`, check for overlays |
| Dialog not responding | Close with `browser_press_key(key="Escape")` |
| Page stale | `browser_navigate` to refresh |

---

## Best Practices

1. **Always snapshot first** - Get refs before any action
2. **Use refs for disambiguation** - Multiple "Post" buttons? Use exact ref
3. **Wait after actions** - 1-2 seconds for React re-renders
4. **Verify before "done"** - Take final snapshot to confirm result
5. **Follow dialog sequences** - select → confirm → submit → verify

---

## Facebook UI Notes

- **React/SPA** - Elements re-render; always refresh snapshot after changes
- **Portals** - Dialogs render outside parent containers
- **Overlays** - Multiple modals can stack; use `force=True`
- **Lazy loading** - Scroll to load more content
- **Privacy button** - Shows CURRENT setting, not a fixed label