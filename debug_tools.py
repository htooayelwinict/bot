import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from playwright.async_api import async_playwright
from src.tools import (
    browser_navigate,
    browser_get_snapshot,
    browser_get_page_info,
    browser_wait,
    browser_click,
    capture_screenshot_for_analysis
)

async def main():
    print("STARTING TOOL TESTS...")
    try:
        async with async_playwright() as p:
            print("Launching browser...")
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            print("\n1. Testing browser_navigate...")
            res = await browser_navigate(url="https://example.com", page=page)
            print(f"Result: {res}")

            print("\n2. Testing browser_get_page_info...")
            res = await browser_get_page_info(page=page)
            print(f"Result: {str(res)[:200]}...") 

            print("\n3. Testing browser_get_snapshot...")
            res = await browser_get_snapshot(page=page)
            print(f"Snapshot Output:\n{res}\n")
            
            # Extract ref for "Learn more" (was "More information...")
            import re
            match = re.search(r'link "Learn more"', str(res))
            if match:
                # Manual extraction from the printed output above
                # In strict test we'd regex the [ref=eX] part
                match_ref = re.search(r'link "Learn more".*: \[ref=(e\d+)\]', str(res))
                if match_ref: 
                    ref_id = match_ref.group(1)
                    print(f"Found ref for link: {ref_id}")
                    
                    print(f"\n3b. Testing browser_click(ref='{ref_id}')...")
                    res = await browser_click(ref=ref_id, page=page)
                    print(f"Result: {res}")
                    
                     # Wait for nav
                    await page.wait_for_load_state()
                    print(f"New URL: {page.url}")

                    if "iana.org" in page.url:
                         print("SUCCESS: Ref-based navigation confirmed")
                    else:
                         print("FAILURE: URL did not change to iana.org")
                else:
                    print("FAILURE: Found link text but could not extract ref")
            else:
                print("FAILURE: Could not find 'Learn more' link in snapshot")

            print("\n4. Testing browser_wait (time)...")
            res = await browser_wait(time=1, page=page)
            print(f"Result: {res}")

            print("\n5. Testing browser_click (text)...")
            # Example.com has a link "More information..."
            res = await browser_click(selector="text='More information...'", page=page)
            print(f"Result: {res}")
            
            # Wait for nav
            await page.wait_for_load_state()
            print(f"New URL: {page.url}")

            if "iana.org" in page.url:
                 print("SUCCESS: Navigation confirmed")
            else:
                 print("FAILURE: URL did not change to iana.org")

            print("\n6. Testing browser_get_snapshot (ref generation on new page)...")
            res = await browser_get_snapshot(page=page)
            print(f"Result length: {len(str(res))}")
            
            print("\n7. Testing capture_screenshot_for_analysis...")
            res = await capture_screenshot_for_analysis(page=page)
            print(f"Result: {str(res)[:100]}...")

            await browser.close()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: {e}")
    
    print("\nTESTS COMPLETED.")

if __name__ == "__main__":
    asyncio.run(main())
