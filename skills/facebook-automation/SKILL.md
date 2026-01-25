---
name: facebook-automation
description: Facebook automation including posting with privacy settings, interactions, messaging, and navigation workflows
allowed-tools: browser_navigate browser_click browser_type browser_fill_form browser_get_snapshot browser_screenshot browser_wait browser_navigate_back browser_get_page_info browser_hover browser_press_key browser_evaluate browser_scroll write_todos browser_extract_posts
---

# Facebook Automation Skill

Automation guide for Facebook web interface - posts, privacy settings, interactions, and navigation.

## When to Use This Skill
- Create posts with specific privacy settings (Public, Friends, Only me)
- Navigate Facebook pages and features
- Interact with posts (like, comment, share)
- Send messages via Messenger

**If you received a Success Plan with `working_selectors`, try those patterns first.**

---

## Critical Rules

### 🚫 NEVER USE browser_evaluate FOR CLICKING (CAUSES INFINITE LOOPS)

**STOP! If you're about to use browser_evaluate to click, DON'T.**

This is the #1 cause of agent failures. browser_evaluate for clicking:
- Returns null (element not found in DOM)
- Agent retries with different JS variations
- Loops 25+ times, never works

**If browser_evaluate returns null ONCE:**
1. STOP immediately
2. Call `browser_get_snapshot()`
3. Use `browser_click(ref="eXX", force=True)` with ref from snapshot
4. If element not in snapshot, the dialog may not have opened - see "Dialog Not Opening" below

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

### � DIALOG NOT OPENING?

If you clicked to open a dialog but snapshot doesn't show dialog elements:
1. `browser_wait(time=2)` - give React time to render
2. `browser_get_snapshot()` - check again
3. If still no dialog, try clicking again with `force=True`
4. If still fails after 2 attempts, report the issue

### 🔄 LOOP PREVENTION

**If same action fails 2 times:**
1. STOP trying that approach
2. Try DIFFERENT strategy (different tool, different selector)
3. Get fresh snapshot
4. Example: If `browser_evaluate` returns null 2x → Use `browser_click` with ref

**DO NOT repeat the same failed pattern more than 2 times.**

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
| **Max 2 retries per approach** | If it fails twice, try different strategy |

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

## Facebook Post Selectors (CRITICAL - 2025)

**⚠️ WRONG SELECTORS (Don't Use):**
- `article` - Facebook doesn't use semantic HTML articles
- `div[role="article"]` - Posts don't have this ARIA role
- `div[data-ad-preview="message"]` - Only works for ads, not organic posts

**✅ CORRECT SELECTORS FOR FACEBOOK POSTS (2025):**

### Method 1: data-testid Selectors (Most Reliable)

```python
# Feed container
"div[role='feed']"

# Individual posts
"div[data-testid='feed_story']"

# Post content elements
"div[data-testid='post_message']"          # Post text
"a[data-testid='story_author_link']"        # Author link
"span[data-testid='story_timestamp']"       # Timestamp
"img[data-testid='story_photo']"            # Post images
"div[data-testid='feed_loading_indicator']" # Loading spinner (lazy load)
```

### Method 2: ARIA Role-Based Selectors (Resilient)

```python
# Use getByRole pattern (most stable against DOM changes)
page.get_by_role("feed")                     # Feed container
page.get_by_role("article")                  # Individual posts (if present)
page.get_by_role("link", name="author")      # Author links
page.get_by_role("img")                      # Images
```

### Method 3: ARIA Snapshot Refs (Preferred for Interaction)

```python
# 1. Get snapshot
browser_get_snapshot()

# 2. Parse snapshot YAML to find post refs
# Posts appear as "generic" or custom roles with accessible names

# 3. Use refs for precise interaction
browser_click(ref="e42", force=True)
```

### Post Extraction Workflow (Full Example)

```python
# Step 1: Navigate to feed
browser_navigate(url="https://www.facebook.com")
browser_wait(time=2)

# Step 2: Get initial snapshot
browser_get_snapshot()

# Step 3: Scroll to load more posts (lazy loading)
browser_scroll(direction="down", amount=500)
browser_wait(time=2)  # Wait for lazy load to complete

# Step 4: Get fresh snapshot with new posts
browser_get_snapshot()

# Step 5: Extract posts using correct selectors
posts = await page.locator("div[data-testid='feed_story']").all()

# Step 6: Parse each post for content
for post in posts:
    author = post.locator("a[data-testid='story_author_link']")
    text = post.locator("div[data-testid='post_message']")
    timestamp = post.locator("span[data-testid='story_timestamp']")
```

### Lazy Loading Detection

```python
# Check if more posts are loading
loading = await page.locator("div[data-testid='feed_loading_indicator']").count() > 0

# Scroll until no new content appears
prev_count = 0
while True:
    await page.locator("div[data-testid='feed_story']").count() == prev_count:
        browser_scroll(direction="down", amount=500)
        browser_wait(time=2)
        current_count = await page.locator("div[data-testid='feed_story']").count()
        if current_count == prev_count:
            break  # No new posts loaded
        prev_count = current_count
```

### Selector Priority (Use This Order)

1. **data-testid** attributes (most stable) - `div[data-testid='feed_story']`
2. **ARIA roles** - `div[role='feed']`
3. **ARIA snapshot refs** - Use after `browser_get_snapshot()`
4. **User-facing names** - `button="Post"`, `text="Like"`
5. **CSS selectors** (last resort) - Brittle, breaks often

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

**⚠️ CRITICAL: Privacy button has DYNAMIC name**

The privacy button's accessible name includes the current setting PLUS dynamic friend names:
- Full name: `"Edit privacy. Sharing with [setting]"`
- Setting can be: "Public", "Friends", "Only me", "Friends except: [names]"

**ALWAYS use the STABLE PREFIX (never match dynamic suffix):**

| Current Privacy | Full Accessible Name | ALWAYS Use This Selector |
|-----------------|----------------------|--------------------------|
| Public | "Edit privacy. Sharing with Public" | `button="Edit privacy. Sharing with"` |
| Friends | "Edit privacy. Sharing with Friends" | `button="Edit privacy. Sharing with"` |
| Only me | "Edit privacy. Sharing with Only me" | `button="Edit privacy. Sharing with"` |
| Friends except | "Edit privacy. Sharing with Friends except: John, Jane..." | `button="Edit privacy. Sharing with"` |

**WRONG:** ❌ `button="Friends except..."` (dynamic suffix, will fail)
**WRONG:** ❌ `button="Public"` (doesn't match full name)
**CORRECT:** ✅ `button="Edit privacy. Sharing with"` (stable prefix)

**In privacy dialog (after clicking privacy button):**

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
# Look for button starting with "Edit privacy. Sharing with" [ref=eXX]

# 5. Click privacy button using STABLE PREFIX selector
browser_click(selector='button="Edit privacy. Sharing with"', force=True)
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

# 8b. CRITICAL - Refresh snapshot after typing (refs become stale)
browser_get_snapshot()

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
6. **Scroll down/up to load more posts** - if you want more posts beyond what's in the snapshot, you should scroll down/up the webpage

---

## Facebook UI Notes

- **React/SPA** - Elements re-render; always refresh snapshot after changes
- **Portals** - Dialogs render outside parent containers
- **Overlays** - Multiple modals can stack; use `force=True`
- **Lazy loading** - Scroll to load more content
- **Privacy button** - Shows CURRENT setting, not a fixed label