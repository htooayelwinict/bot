---
name: facebook-automation
description: Comprehensive Facebook automation including posting, stories, messaging, groups, marketplace, and all interaction workflows
allowed-tools: browser_navigate browser_click browser_type browser_fill_form browser_get_snapshot browser_screenshot browser_wait browser_navigate_back browser_get_page_info browser_hover browser_press_key browser_evaluate browser_scroll
---

# Facebook Automation Skill

Complete automation guide for Facebook web interface including News Feed, Posts, Stories, Messenger, Groups, Marketplace, and account management.

## When to Use This Skill
- Navigate and interact with Facebook pages
- Create, edit, or delete posts with privacy settings
- Interact with posts (like, comment, share, save)
- Send messages via Messenger
- Manage groups (create, post, moderate)
- Browse and interact with Marketplace
- Manage Stories
- Handle notifications
- Search for people, pages, or content
- Manage account settings and privacy

## Prerequisites
- Facebook session authenticated via session manager
- Browser context available with `set_current_async_page()`
- Stable internet connection (Facebook is JS-heavy)

---

## Critical Rules

### Mandatory Decision Process (Before ANY Click)
**Before clicking ANYTHING, you MUST:**

1. **Collect**: Get snapshot with all refs
   ```
   browser_get_snapshot()
   ```

2. **Analyze**: Explicitly list ALL visible elements:
   ```
   # From snapshot I see:
   # - button "Public" [ref=e15] <- Privacy button
   # - button "Photo/video" [ref=e16] <- NOT what I need
   # - button "Tag people" [ref=e17] <- NOT what I need
   ```

3. **Reason**: State which ref matches your goal and why
   ```
   # I need to change privacy, so I will click ref=e15 (Public button)
   ```

4. **Act**: Click with specific ref
   ```
   browser_click(ref="e15", force=True)
   ```

**NEVER click without analyzing first!**

### Must-Follow Principles
1. **NEVER say "done" until verified** - Use `browser_get_snapshot` to confirm final state
2. **Complete ALL dialog steps** - Selecting an option ≠ confirming it (must click Done/Save/Post)
3. **Always use `force=True`** - Facebook has invisible overlays that block clicks
4. **Wait after actions** - `browser_wait(time=1-2)` for React to re-render
5. **Snapshot before AND after** - See state, act, verify result

### Ref-Based Targeting (Playwright 1.49+ ARIA Snapshot)
The tools use Playwright's `locator.aria_snapshot()` API for precise element selection:

1. **Get snapshot with refs**: `browser_get_snapshot()` returns YAML-like ARIA tree with `[ref=eN]` markers
2. **Analyze ALL refs**: List each element with its ref and function
3. **Match goal to ref**: Choose the correct ref based on your task
4. **Use ref for precise targeting**: `browser_click(ref="e42")` clicks exact element

**ARIA Snapshot Format:**
```yaml
- navigation "Facebook":
  - link "Home" [ref=e0]
  - button "Search" [ref=e1]
- main:
  - button "What's on your mind?" [ref=e15]
  - textbox "Write something..." [ref=e16]
```

**Why use refs?**
- Disambiguates multiple elements with same text (e.g., multiple "Post" buttons)
- Targets specific dialog-scoped elements
- More reliable than selector matching
- Auto-generated from accessibility tree

**Ref Lifecycle:**
- Refs are assigned sequentially (`e0`, `e1`, `e2`...)
- Refs expire when page changes - refresh with `browser_get_snapshot()`
- Refs timeout after 30 seconds - refresh if stale

### Facebook UI Quirks
- Uses React with virtual DOM - elements may re-render after interactions
- Heavy use of portals - dialogs render outside parent containers
- Lazy loading - scroll to load more content
- Aggressive caching - may need page refresh for state changes
- Multiple overlays - modals stack, need to close in order

---

## Tool API Reference

> **Technical Note:** Tools use Playwright 1.49+ `locator.aria_snapshot()` API for accessibility snapshots.
> This returns a YAML-like format with role-based element identification.

### browser_get_snapshot
Get ARIA accessibility snapshot with element refs. **Always call this first** to get refs for targeting.

```
browser_get_snapshot()
```

**Output format** (YAML-like ARIA snapshot):
```yaml
- navigation "Facebook":
  - link "Home" [ref=e0]
  - link "Watch" [ref=e1]
  - link "Marketplace" [ref=e2]
- main:
  - button "What's on your mind?" [ref=e15]
  - article:
    - button "Like" [ref=e28]
    - button "Comment" [ref=e29]
    - button "Share" [ref=e30]
```

**Key concepts:**
- Each element gets a unique `[ref=eN]` marker
- Refs are assigned sequentially starting from `e0`
- Refs are page-scoped - refresh after navigation
- Snapshot expires after 30 seconds

### browser_click
Click on an element using ref or selector.
```
# Ref-based (recommended - targets exact element from snapshot)
browser_click(ref="e42", force=True)

# Selector-based (fallback when refs unavailable)
browser_click(selector="button=Post", force=True)
```

**Important:** Use `force=True` for Facebook - overlays block normal clicks.

### browser_type
Type text into an input field.
```
# Ref-based (recommended)
browser_type(ref="e23", text="Hello world")

# Selector-based (fallback)
browser_type(selector="div[contenteditable='true']", text="Hello world")
```

### browser_wait
Wait for UI to update after actions.
```
browser_wait(time=1)  # Wait 1 second
browser_wait(time=2)  # Wait 2 seconds (use for navigation)
```

### browser_hover
Hover over element (reveals hidden UI like reactions).
```
browser_hover(ref="e28")  # Hover over Like button to show reactions
```

### browser_press_key
Press keyboard key (Enter, Tab, Escape, etc.).
```
browser_press_key(key="Enter")   # Submit form
browser_press_key(key="Escape")  # Close dialog
```

### browser_navigate
Navigate to a URL.
```
browser_navigate(url="https://www.facebook.com")
```

### browser_screenshot
Capture screenshot (useful for debugging).
```
browser_screenshot(path="debug.png")
```

---

## Selector Reference

### Priority Order (most reliable first)
1. **ref from snapshot** - Use `browser_get_snapshot()` first, then `ref="e42"` (MOST RELIABLE)
2. `button=Button Name` - Buttons shown as `button "Name"` in snapshot
3. `text=Visible Text` - Clickable visible text
4. `radio=Option Text` - Radio buttons in dialogs
5. `[aria-label="Label"]` - Aria-label attributes
6. `[data-testid="testid"]` - Test IDs (stable but not always present)
7. `div[contenteditable='true'][role='textbox']` - Rich text inputs
8. CSS selectors as fallback

### Common Facebook Selectors (for selector parameter)

#### Navigation
| Element | Selector |
|---------|----------|
| Home | `[aria-label="Home"]` or `text=Home` |
| Profile | `[aria-label="Your profile"]` or `text=Your Profile` |
| Messenger | `[aria-label="Messenger"]` |
| Notifications | `[aria-label="Notifications"]` |
| Menu | `[aria-label="Menu"]` |
| Search | `[aria-label="Search Facebook"]` |
| Watch | `text=Watch` |
| Marketplace | `text=Marketplace` |
| Groups | `text=Groups` |

#### Post Composer
| Element | Selector |
|---------|----------|
| Open composer | `button=What's on your mind?` |
| Text input | `div[contenteditable='true'][role='textbox']` |
| Photo/Video | `[aria-label="Photo/video"]` or `text=Photo/video` |
| Tag people | `[aria-label="Tag people"]` or `text=Tag people` |
| Feeling/Activity | `[aria-label="Feeling/activity"]` |
| Check in | `[aria-label="Check in"]` |
| GIF | `[aria-label="GIF"]` |
| Live video | `text=Live video` |
| Post button | `button=Post` |
| Next button | `button=Next` |

#### Privacy/Audience
| Element | Selector |
|---------|----------|
| Audience selector | `button=Public` or `button=Friends` (shows CURRENT setting) - **IMPORTANT: The button text changes! Look for the button showing current privacy (Public/Friends/Only me), NOT "Post audience" |
| Privacy - Public | `radio=Public` |
| Privacy - Friends | `radio=Friends` |
| Privacy - Only me | `radio=Only me` |
| Privacy - Custom | `radio=Custom` |
| Done button | `button=Done` |

**CRITICAL: The privacy button shows the CURRENT setting, not a fixed name:**
- If privacy is currently "Public", the button says `Public`
- If privacy is currently "Friends", the button says `Friends`
- If privacy is currently "Only me", the button says `Only me`
- Get a snapshot FIRST to see what the current setting is!

#### Post Interactions
| Element | Selector |
|---------|----------|
| Like button | `[aria-label="Like"]` or `button=Like` |
| Love reaction | `[aria-label="Love"]` |
| Comment button | `[aria-label="Leave a comment"]` or `button=Comment` |
| Share button | `[aria-label="Send this to friends or post it on your profile"]` or `button=Share` |
| Save post | `text=Save post` |
| More options | `[aria-label="Actions for this post"]` |

#### Messenger
| Element | Selector |
|---------|----------|
| New message | `[aria-label="New message"]` |
| Message input | `[aria-label="Message"]` or `div[contenteditable='true'][role='textbox']` |
| Send button | `[aria-label="Press enter to send"]` |
| Search messages | `[aria-label="Search Messenger"]` |

---

## Core Workflows

### 1. Navigation

#### Go to Facebook Home
```
browser_navigate(url="https://www.facebook.com")
browser_wait(time=2)
browser_get_snapshot()  # Verify logged in, see News Feed
```

#### Navigate via Left Sidebar
```
browser_click(ref="e15", force=True)  # e15 from snapshot for "Groups"
browser_wait(time=2)
browser_get_snapshot()
```

#### Navigate via Top Bar
```
browser_click(ref="e8", force=True)  # e8 from snapshot for Messenger icon
browser_wait(time=1)
browser_get_snapshot()
```

---

### 2. Creating Posts

#### Basic Post (Agent Workflow - Ref-Based)

**CRITICAL: Refs are dynamic - agent MUST fetch snapshot first, then use refs from that snapshot.**

```
# Step 1: Navigate to Facebook
browser_navigate(url="https://www.facebook.com")
browser_wait(time=2)

# Step 2: Get snapshot to find element refs
snapshot = browser_get_snapshot()
# Find ref for button containing "What's on your mind"

# Step 3: Open post composer
browser_click(selector='button="What\'s on your mind, [user]?"', force=True)
browser_wait(time=1)

# Step 4: Get snapshot for composer dialog
snapshot = browser_get_snapshot()
# Find textbox ref for typing content

# Step 5: Type content
browser_type(selector="role=textbox", text="Your post content here")
browser_wait(time=1)

# Step 6: Click Next to open post settings
browser_click(selector='button="Next"', force=True)
browser_wait(time=2)

# Step 7: Get snapshot for post dialog
snapshot = browser_get_snapshot()
# Find Post button ref

# Step 8: Publish
browser_click(selector='role=button[name="Post"][exact]', force=True)
browser_wait(time=3)

# Step 9: Verify
snapshot = browser_get_snapshot()
# Confirm post appears in feed
```

#### Basic Post (Using Selectors - Fallback)
```
# Step 1: Open composer
browser_click(selector="button=What's on your mind?", force=True)
browser_wait(time=1)
browser_get_snapshot()

# Step 2: Type content
browser_type(selector="div[contenteditable='true'][role='textbox']", text="Your post content here")
browser_wait(time=0.5)

# Step 3: Post
browser_click(selector="button=Post", force=True)
browser_wait(time=2)

# Step 4: Verify
browser_get_snapshot()  # Must see post in feed
```

#### Post with Privacy Setting (Only Me) - Complete Flow

```
# Step 1: Navigate to Facebook
browser_navigate(url="https://www.facebook.com")
browser_wait(time=2)

# Step 2: Get snapshot
snapshot = browser_get_snapshot()

# Step 3: Open post composer
browser_click(selector='button="What\'s on your mind, [user]?"', force=True)
browser_wait(time=1)

# Step 4: Get snapshot for composer - CRITICAL to find privacy button
snapshot = browser_get_snapshot()
# Look for button showing CURRENT privacy setting (Public/Friends/Only me)
# DO NOT click Photo, Feeling, GIF, or other toolbar buttons!

# Step 5: Click privacy button (shows current setting, e.g., "Public")
# Check snapshot to see what it shows, then click that button
browser_click(selector='button=Public', force=True)  # or Friends, Only me - whatever current is
browser_wait(time=0.5)

# Step 6: Get snapshot for privacy dialog
snapshot = browser_get_snapshot()

# Step 7: Select "Only me" option (radio button)
browser_click(selector='radio=Only me', force=True)
browser_wait(time=0.5)

# Step 8: CRITICAL - Confirm privacy selection
browser_click(selector='button="Done"', force=True)
browser_wait(time=0.5)

# Step 9: Get snapshot for typing
snapshot = browser_get_snapshot()

# Step 10: Type the post content
browser_type(selector="role=textbox", text="Your private message here")
browser_wait(time=1)

# Step 11: Click Next to open post settings
browser_click(selector='button="Next"', force=True)
browser_wait(time=2)

# Step 12: Get snapshot for post dialog
snapshot = browser_get_snapshot()

# Step 13: Click Post (use exact match to avoid wrong Post button)
browser_click(selector='role=button[name="Post"][exact]', force=True)
browser_wait(time=3)

# Step 14: Verify post created
snapshot = browser_get_snapshot()
# Confirm post visible in feed with "Only me" privacy indicator
```

#### Changing Privacy Settings (General Pattern)

Privacy options available in Facebook post composer:

| Privacy Level | Selector |
|---------------|----------|
| Public | `radio=Public` |
| Friends | `radio=Friends` |
| Friends except... | `radio=Friends except...` |
| Specific friends | `radio=Specific friends` |
| Only me | `radio=Only me` |
| Custom | `radio=Custom` |

**Workflow to change any privacy setting:**
```
# After opening post composer (Steps 1-4 above)

# Step 5: Click privacy button (shows CURRENT setting - check snapshot!)
# The button will say "Public" or "Friends" or "Only me" - click whatever it shows
browser_click(selector='button=Public', force=True)  # or Friends, Only me - match current!
browser_wait(time=0.5)

# Step 6: Get snapshot for privacy dialog
snapshot = browser_get_snapshot()

# Step 7: Select desired privacy option (radio button)
browser_click(selector='radio=Only me', force=True)  # or Public, Friends, etc.
browser_wait(time=0.5)

# Step 8: CRITICAL - Confirm selection with Done
browser_click(selector='button="Done"', force=True)
browser_wait(time=0.5)

# Continue with typing and posting (Steps 9-14 above)
```

---

### 3. Post Interactions

#### Like a Post (Using Refs)
```
browser_get_snapshot()  # Get refs
browser_click(ref="e28", force=True)  # Like button ref
browser_wait(time=0.5)
browser_get_snapshot()  # Verify liked
```

#### React to Post (Love, Haha, etc.)
```
# Hover to reveal reactions
browser_hover(ref="e28")  # Like button
browser_wait(time=1)
browser_get_snapshot()

# Click specific reaction
browser_click(ref="e35", force=True)  # Love reaction ref
browser_wait(time=0.5)
browser_get_snapshot()
```

#### Comment on Post
```
browser_get_snapshot()

browser_click(ref="e32", force=True)  # Comment button
browser_wait(time=0.5)

browser_type(ref="e45", text="Great post!")  # Comment input ref
browser_press_key(key="Enter")
browser_wait(time=1)
browser_get_snapshot()  # Verify comment appears
```

---

### 4. Messenger

#### Send Message
```
browser_get_snapshot()

browser_click(ref="e10", force=True)  # Messenger icon
browser_wait(time=1)

browser_click(ref="e55", force=True)  # Chat ref
browser_wait(time=1)

browser_type(ref="e60", text="Hey! How are you?")  # Message input ref
browser_press_key(key="Enter")
browser_wait(time=1)
browser_get_snapshot()
```

---

### 5. Groups

#### Post in Group
```
browser_navigate(url="https://www.facebook.com/groups/groupid")
browser_wait(time=2)
browser_get_snapshot()

browser_click(ref="e20", force=True)  # Write something button
browser_wait(time=1)

browser_type(ref="e25", text="Group post content")  # Textbox ref

browser_click(ref="e30", force=True)  # Post button ref
browser_wait(time=2)
browser_get_snapshot()
```

---

## Troubleshooting

### Ref Not Found
1. Take a fresh snapshot: `browser_get_snapshot()`
2. Find the correct ref for the element
3. Elements change after interactions - refresh snapshot
4. Refs are page-scoped - refresh after navigation

### Element Not Found
1. Run `browser_get_snapshot()` to see current state
2. Use ref from snapshot instead of selector
3. Element may be in a modal/dialog - check for overlay
4. Page may not be fully loaded - add `browser_wait(time=2)`

### Click Not Working
1. Add `force=True` parameter
2. Check for overlays blocking the element
3. Try hovering first: `browser_hover(ref)` then `browser_click(ref)`
4. Increase wait time before clicking
5. Try JavaScript click: `browser_evaluate(function="document.querySelector('selector').click()")`

---

## Best Practices

### Always Follow This Pattern
```
1. browser_get_snapshot()     # Get refs, see current state
2. browser_click(ref="e42")   # Use ref for precise targeting
3. browser_wait(time=1)       # Let UI update
4. browser_get_snapshot()     # Verify result
```

### When to Refresh Snapshot
- After navigating to new page
- After clicking that opens/closes dialogs
- After form submissions
- If ref resolution fails
- When UI state changes significantly

### Performance Tips
- Use refs for disambiguation (multiple elements with same text)
- Use `force=True` proactively to avoid retry loops
- Keep wait times reasonable (1-2 seconds usually sufficient)
- Refresh snapshot only when needed (not after every action)

### Security Reminders
- Never log credentials in output
- Use "Only me" privacy for test posts
- Be careful with automated posting (rate limits)
- Respect Facebook's Terms of Service
---

## Technical Implementation Notes

> For developers extending or debugging this skill.

### Playwright Version Requirements
- **Minimum:** Playwright 1.49+ (for `aria_snapshot()` API)
- **Tested:** Playwright 1.57.0

### ARIA Snapshot API
Tools use `Locator.aria_snapshot()` instead of deprecated `page.accessibility.snapshot()`:

```python
# Old API (removed in Playwright 1.57)
# snapshot = await page.accessibility.snapshot()

# New API (Playwright 1.49+)
locator = page.locator("body").first
aria_text = await locator.aria_snapshot(timeout=10000)
```

### Agent Framework
- **Framework:** DeepAgents (wrapper around LangGraph `create_react_agent`)
- **Model:** Configurable (default: `gpt-4o-mini`)
- **Memory:** `InMemoryStore` + `MemorySaver` checkpointer
- **Skills:** Loaded via `SkillsMiddleware` from filesystem

### Ref Resolution Strategy
When resolving refs to Playwright locators, priority order:
1. `id` attribute (most stable)
2. `data-testid` attribute  
3. `aria-label` attribute
4. Role + exact name + sibling index
5. Role + nth position (fallback)

### Debug Environment Variables
```bash
DEBUG_REFS=true  # Enable ref operation logging
```