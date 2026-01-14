import re
import asyncio
import sys
import os
import re
from pathlib import Path

print("PROGRAM STARTING...")

# Add current directory to path
sys.path.append(os.getcwd())

from playwright.async_api import async_playwright
from src.session import FacebookSessionManager
from src.tools import (
    browser_navigate,
    browser_get_snapshot,
    browser_click,
    browser_type,
    browser_wait,
    capture_screenshot_for_analysis
)
from src.tools.base import set_current_async_page

async def find_ref(snapshot_text, pattern_description, role=None, strict=False):
    """
    Robust ref finder.
    Args:
        snapshot_text: The full YAML snapshot
        pattern_description: Text to find (e.g. "Post")
        role: Optional role to filter by (e.g. "button")
        strict: If True, requires strict equality for name match
    """
    print(f"   🔎 Searching for: '{pattern_description}' (role={role})...")
    
    lines = snapshot_text.split('\n')
    candidates = []
    
    for line in lines:
        if "[ref=" not in line:
            continue
            
        # Parse line: - role "name" [ref=eX]
        # Regex to capture: role, name, ref
        # Typical line: - button "Post" [ref=e100]
        # Or: - div [ref=e20]
        match = re.search(r'-\s+(\w+)(?:\s+"([^"]*)")?.*\[ref=(e\d+)\]', line)
        if match:
            item_role = match.group(1)
            item_name = match.group(2) or ""
            item_ref = match.group(3)
            
            # Filter by role if specified
            if role and item_role != role:
                continue
                
            # Check name match
            if strict:
                if item_name.strip() == pattern_description:
                    print(f"   ✅ STRICT match: {line.strip()}")
                    return item_ref
            else:
                # Loose match
                if pattern_description.lower() in item_name.lower():
                    # Prioritize exact match if multiple loose matches found? 
                    # For now just return first, but print it
                    print(f"   ✅ Found candidate: {line.strip()}")
                    candidates.append((item_ref, item_name, line.strip()))

    if candidates:
        # If we have multiple candidates, prefer the shortest name (closest to exact match)
        # e.g. "Post" vs "Create Post"
        candidates.sort(key=lambda x: len(x[1]))
        if strict:
             # Should have returned above, but double check
             for c in candidates:
                 if c[1] == pattern_description: return c[0]
        else:
             best = candidates[0]
             print(f"   👉 Selected best match: {best[2]}")
             return best[0]

    print(f"   ❌ Could not find ref for '{pattern_description}'")
    return None

async def main():
    print("🚀 Starting Facebook Post Test (Only Me) - ROBUST MODE...")
    
    # Ensure profile directory exists
    profile_path = Path("./profiles/facebook")
    if not profile_path.exists():
        print(f"❌ Profile directory not found at {profile_path}")
        return

    session_manager = FacebookSessionManager(profile_dir=profile_path, headless=False)
    
    async with async_playwright() as p:
        print("   Loading profile...")
        # Load profile
        context, page, restored = await session_manager.get_or_create_session_async(p.chromium)
        
        # Inject page into tools context
        set_current_async_page(page)
        
        if not restored:
            print("   ⚠️  Session was NOT restored. You may need to log in manually.")
        else:
            print("   ✅ Session restored.")
        
        # 1. Navigate
        print("\n1. Navigating to Facebook...")
        await browser_navigate(url="https://facebook.com", page=page)
        await browser_wait(time=4, page=page) # Initial load
        
        # 2. Find "What's on your mind"
        print("\n2. Finding Post Creator...")
        snap = await browser_get_snapshot(page=page)
        
        # Look for the button specifically
        ref = await find_ref(snap, "What's on your mind", role="button")
        
        if not ref:
             print("   ⚠️  Ref not found via snapshot. Dumping snapshot to see what's there...")
             print(snap[:2000]) # First 2000 chars
             
             print("   Trying generic selector fallback...")
             try:
                await page.click("div[role='button'] span:has-text('What')", timeout=2000)
                print("   ✅ Fallback click success")
             except:
                print("   ❌ Fallback failed.")
                return
        else:
             await browser_click(ref=ref, page=page)
             
        await browser_wait(time=3, page=page)
        
        # 3. Find Privacy Selector (Robust)
        print("\n3. Finding Privacy Selector...")
        snap = await browser_get_snapshot(page=page)
        
        # Strategies to find the privacy button:
        # 1. Look for specific known current states
        privacy_btn_ref = await find_ref(snap, "Sharing with Public", role="button") or \
                          await find_ref(snap, "Sharing with Friends", role="button") or \
                          await find_ref(snap, "Sharing with Only me", role="button") or \
                          await find_ref(snap, "Public", role="button") or \
                          await find_ref(snap, "Friends", role="button") or \
                          await find_ref(snap, "Only me", role="button")

        if privacy_btn_ref:
            # Check if we need to change it
            # We need to know the *name* of the button we found to check current state
            # Re-fetch the line for this ref
            btn_line = [l for l in snap.split('\n') if f"[ref={privacy_btn_ref}]" in l][0]
            print(f"   found privacy button: {btn_line}")
            
            if "Only me" in btn_line:
                print("   ✅ Privacy is ALREADY 'Only me'.")
            else:
                print("   🔄 Need to change privacy to 'Only me'. Clicking selector...")
                await browser_click(ref=privacy_btn_ref, page=page)
                await browser_wait(time=2, page=page)
                
                # Now inside the dialog
                snap_dialog = await browser_get_snapshot(page=page)
                
                # Verify we are in the dialog
                if "Select audience" in snap_dialog or "Post audience" in snap_dialog:
                    print("   In Audience Dialog.")
                    
                    # Search for "Only me"
                    only_me_ref = await find_ref(snap_dialog, "Only me", role="radio") or \
                                  await find_ref(snap_dialog, "Only me", role="button") # Sometimes it's a list item/button
                    
                    if not only_me_ref:
                         print("   'Only me' not visible. Checking for 'More'...")
                         # Sometimes hidden under "More"
                         more_ref = await find_ref(snap_dialog, "More", role="button")
                         if more_ref:
                             await browser_click(ref=more_ref, page=page)
                             await browser_wait(time=1, page=page)
                             snap_dialog = await browser_get_snapshot(page=page) # Refresh
                             only_me_ref = await find_ref(snap_dialog, "Only me")
                    
                    if only_me_ref:
                        print("   Clicking 'Only me'...")
                        await browser_click(ref=only_me_ref, page=page)
                        await browser_wait(time=1, page=page)
                        
                        # Click Done if it exists
                        snap_dialog = await browser_get_snapshot(page=page)
                        done_ref = await find_ref(snap_dialog, "Done", role="button")
                        if done_ref:
                             await browser_click(ref=done_ref, page=page)
                             await browser_wait(time=2, page=page)
                        else:
                             # Sometimes clicking the radio closes it, or there is a back button
                             print("   No Done button found, assuming selection handled or auto-closed.")
                    else:
                        print("   ❌ CAUTION: Could not find 'Only me' option even after looking.")
                else:
                    print("   ⚠️  Clicking privacy button didn't seem to open Audience dialog.")
            
            # --- Verification of Privacy Setting ---
            print("   Verifying Privacy Selection...")
            await browser_wait(time=1, page=page)
            snap_verify_priv = await browser_get_snapshot(page=page)
            if "Only me" in snap_verify_priv or "Sharing with Only me" in snap_verify_priv:
                 print("   ✅ Verified: Privacy is set to 'Only me'.")
            else:
                 print("   ⚠️  WARNING: Privacy verification failed. Button does not say 'Only me'.")
        else:
            print("   ⚠️  Privacy selector NOT found. Proceeding with default.")

        # 6. Type content
        print("\n6. Typing content...")
        snap = await browser_get_snapshot(page=page)
        
        # Textbox often has role "textbox" and label "What's on your mind"
        textbox_ref = await find_ref(snap, "What's on your mind", role="textbox")
        
        unique_text = f"Automated test post {int(asyncio.get_event_loop().time())}"

        if textbox_ref:
            await browser_type(ref=textbox_ref, text=unique_text, page=page)
        else:
            print("   ⚠️  Could not find textbox ref. Using basic keyboard input.")
            await page.keyboard.type(unique_text)
            
        await browser_wait(time=2, page=page)
        
        # 7. Post
        print("\n7. Posting...")
        snap = await browser_get_snapshot(page=page)
        
        # IMPORTANT: Search for BUTTON with exact name "Post"
        post_btn_ref = await find_ref(snap, "Post", role="button", strict=True)
        
        if not post_btn_ref:
            # Try again non-strict but check it's not the dialog
            post_btn_ref = await find_ref(snap, "Post", role="button")

        if post_btn_ref:
            await browser_click(ref=post_btn_ref, page=page)
            print("   ✅ Clicked Post Button")
            
            # Wait for post to complete (dialog disappear)
            await browser_wait(time=5, page=page)
            
            # 8. Verify and Get Link
            print("\n8. Verifying Post and Creating Proof...")
            # Go to profile
            print("   Navigating to Profile...")
            await browser_navigate(url="https://facebook.com/me", page=page)
            await browser_wait(time=5, page=page)
            
            snap_verify = await browser_get_snapshot(page=page)
            
            found_text = False
            if unique_text in snap_verify:
                print(f"   🎉 SUCCESS: Found post text '{unique_text}' on profile!")
                found_text = True
            else:
                 # Try scrolling down a bit
                print("   Not found at top. Scrolling...")
                await page.evaluate("window.scrollBy(0, 500)")
                await browser_wait(time=2, page=page)
                snap_verify = await browser_get_snapshot(page=page)
                if unique_text in snap_verify:
                     print(f"   🎉 SUCCESS: Found post text '{unique_text}' on profile (after scroll)!")
                     found_text = True
                else:
                     print("   ⚠️  Could not find post text on profile.")

            if found_text:
                # Attempt to find the permalink
                print("   Extracting Post URL...")
                try:
                    # Find a link containing "Just now" or "1 m" that is inside the feed
                    post_locator = page.locator(f"div[role='article']:has-text('{unique_text}')").first
                    
                    # --- NEW: Verify Privacy on the Resulting Post ---
                    print("   🕵️‍♀️ Verifying Post Privacy on Feed...")
                    # Facebook posts usually have an icon with aria-label "Shared with X"
                    # We search within the article for any element with "Shared with" in aria-label
                    privacy_icon = post_locator.locator("[aria-label*='Shared with']")
                    if await privacy_icon.count() > 0:
                        privacy_text = await privacy_icon.first.get_attribute("aria-label")
                        print(f"      Found Privacy Status: '{privacy_text}'")
                        if "Only me" in privacy_text or "Only Me" in privacy_text:
                             print("      ✅ FINAL CONFIRMATION: Post is visible as 'Only me'.")
                        else:
                             print(f"      ❌ MISMATCH: Post is '{privacy_text}' (User wanted Only Me)")
                    else:
                        print("      ⚠️  Could not find 'Shared with' icon on the post. Facebook DOM might have changed.")

                    # --- End New Verification ---

                    if await post_locator.count() > 0:
                        # Improved locator for timestamp: explicit HOVER to reveal permalink if needed
                        # Often the timestamp is a link with text "Just now" or "1 m" or "1 min"
                        # We use a regex for time units
                        timestamp_link = post_locator.locator("a").filter(has_text=re.compile(r"Just now|^\d+\s?[mhds]")).first
                        
                        if await timestamp_link.count() > 0:
                            # Hover to ensure tooltips don't block? not needed usually.
                            post_url = await timestamp_link.get_attribute("href")
                            print(f"   (Raw URL found: {post_url})")
                            
                            # Clean URL logic
                            if post_url:
                                if "facebook.com" not in post_url:
                                    post_url = "https://www.facebook.com" + post_url
                                
                                # Only strip query params if it looks like a clean path (e.g. /posts/123)
                                # If it is permalink.php?story_fbid=..., keep it!
                                if "permalink.php" not in post_url and "/posts/" in post_url:
                                     post_url = post_url.split('?')[0]
                                
                                # Verify it's not just the profile link
                                if post_url.rstrip('/') == "https://www.facebook.com/me" or post_url == page.url:
                                     print("   ⚠️  Warning: Extracted URL looks like profile link, not post link.")
                                else:
                                     print(f"\n   🔗 POST LINK: {post_url}\n")
                        else:
                            print("   Could not isolate timestamp link in the article (locator filter failed).")
                            # Fallback: Print all links in the article to debug
                            links = await post_locator.locator("a").all()
                            for i, link in enumerate(links):
                                txt = await link.inner_text()
                                href = await link.get_attribute("href")
                                print(f"      [DEBUG] Link {i}: '{txt}' -> {href}")
                    else:
                         print("   Could not isolate post article element.")
                except Exception as e:
                    print(f"   Error extracting link: {e}")

            # Take Screenshot
            print("   Taking Screenshot Proof...")
            # Ensure we scroll so the post header (with privacy icon) is visible
            await page.evaluate("window.scrollBy(0, -200)") 
            await browser_wait(time=1, page=page)
            result = await capture_screenshot_for_analysis(filename="proof_of_post_onlyme", page=page)
            print(f"   📸 Screenshot result: {result}")
            
        else:
            print("   ❌ CRITICAL: Could not find Post button. Dumping snapshot:")
            print(snap)
            await capture_screenshot_for_analysis(filename="failed_to_find_post_btn", page=page)

        print("Done.")
        print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
