"""
Browser control using Playwright
"""
import asyncio
from typing import Optional, List, Dict, Any
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from pathlib import Path


class BrowserManager:
    """Manage browser instances using Playwright"""

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Initialize browser manager
        
        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout in milliseconds
        """
        self.headless = headless
        self.timeout = timeout
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def start(self):
        """Start browser instance"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.timeout)

    async def navigate(self, url: str, wait_time: int = 5000) -> bool:
        """
        Navigate to URL
        
        Args:
            url: URL to navigate to
            wait_time: Wait time after navigation in milliseconds
            
        Returns:
            True if navigation successful, False otherwise
        """
        try:
            await self.page.goto(url, wait_until='domcontentloaded', timeout=self.timeout)
            await self.page.wait_for_timeout(wait_time)
            return True
        except Exception:
            return False

    async def get_page_source(self) -> str:
        """Get page source HTML"""
        return await self.page.content()

    async def find_elements(self, selector: str) -> List[Any]:
        """
        Find elements by CSS selector
        
        Args:
            selector: CSS selector
            
        Returns:
            List of element handles
        """
        try:
            elements = await self.page.query_selector_all(selector)
            return elements
        except Exception:
            return []

    async def capture_screenshot(self, file_path: str) -> bool:
        """
        Capture screenshot
        
        Args:
            file_path: Path to save screenshot
            
        Returns:
            True if successful, False otherwise
        """
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            await self.page.screenshot(path=file_path, full_page=True)
            return True
        except Exception:
            return False

    async def close(self):
        """Close browser instance"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
