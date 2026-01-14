"""
Facebook Post Creator - Only Me Privacy
Creates a Facebook post with "Only me" privacy setting using Playwright.
"""

async def create_facebook_post_onlyme(page, message: str = "Test post - only me"):
    """
    Create a Facebook post with 'Only me' privacy.

    Args:
        page: Playwright page object (should already be logged into Facebook)
        message: The post content to create
    """

    # Step 1: Navigate to Facebook
    await page.goto('https://facebook.com')

    # Step 2: Close any notification dialogs that might appear
    try:
        await page.get_by_text('Close').click()
    except:
        pass  # No dialog to close

    # Step 3: Click the "What's on your mind" button to open post creator
    await page.get_by_role('button', name="What's on your mind, Htoo?").click()

    # Step 4: Click the privacy button to change audience
    await page.get_by_role('button', name='Edit privacy. Sharing with').click()

    # Step 5: Select "Only me" privacy option
    await page.get_by_text("Only me", exact=True).click()

    # Step 6: Confirm privacy selection by clicking Done
    await page.get_by_role('button', name='Done').click()

    # Step 7: Type the post content
    await page.get_by_role('textbox').fill(message)

    # Step 8: Wait for Next button to enable
    await page.wait_for_timeout(1000)

    # Step 9: Click Next to proceed to post preview
    await page.get_by_role('button', name='Next').click()

    # Step 10: Click Post to publish
    await page.get_by_role('button', name='Post', exact=True).click()

    return True


# Example usage:
# from playwright.async_api import async_playwright
#
# async def main():
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=False)
#         context = await browser.new_context()
#         # Load existing Facebook session/profile here
#         page = await context.new_page()
#
#         result = await create_facebook_post_onlyme(page, "My test post")
#         print(f"Post created: {result}")
#
#         await browser.close()
