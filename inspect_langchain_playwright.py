
import inspect
import asyncio
from typing import Any

try:
    from langchain_community.tools import playwright as playwright_tools
    from langchain_community.tools.playwright.utils import create_async_playwright_browser
    from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
except ImportError as e:
    print(f"Error importing langchain or playwright: {e}")
    exit(1)

def inspect_module():
    print("Available tools in langchain_community.tools.playwright:")
    tools = []
    for name, obj in inspect.getmembers(playwright_tools):
        if inspect.isclass(obj) and "Tool" in name:
            tools.append(name)
            print(f"- {name}")
            # Inspect args
            sig = inspect.signature(obj.__init__)
            print(f"  Init signature: {sig}")
            if hasattr(obj, "_run"):
                run_sig = inspect.signature(obj._run)
                print(f"  _run signature: {run_sig}")
            
            # Check schema if available
            if hasattr(obj, "args_schema") and obj.args_schema:
                print(f"  Args schema: {obj.args_schema.schema()}")

    return tools

async def test_persistent_context():
    print("\nTesting persistent context creation...")
    from playwright.async_api import async_playwright
    
    # Simulate persistent context creation
    try:
        async with async_playwright() as p:
            # We want to see if we can pass a persistent context to the tools
            # Usually tools implementers take 'async_browser' or 'sync_browser'
            # But PlaywrightBrowserToolkit.from_browser takes 'async_browser'
            
            # A persistent context acts like a browser + context
            # Let's see if we can create one and if it has the necessary methods
            
            # This is a mock test since we can't actually spawn a GUI browser easily here without valid display sometimes,
            # but we can check the API surface.
            
            browser = await p.chromium.launch()
            context = await browser.new_context()
            
            # Check if tools accept context instead of browser?
            # Or if we can pass context as 'browser'
            
            print("Successfully created browser and context objects for inspection.")
            
    except Exception as e:
        print(f"Error in playwright test: {e}")

if __name__ == "__main__":
    inspect_module()
    asyncio.run(test_persistent_context())
