"""
Page navigation logic
"""
from typing import List, Tuple, Optional
from playwright.async_api import Page
from auditor.utils import handle_cookie_banner


class Navigator:
    """Handle page navigation and flow"""
    
    def __init__(self, page: Page, headless: bool = True):
        self.page = page
        self.headless = headless
    
    async def navigate_to_home(self, home_url: str) -> bool:
        """Navigate to HOME page"""
        try:
            await self.page.goto(home_url, wait_until='domcontentloaded', timeout=10000)
            await handle_cookie_banner(self.page)
            return True
        except Exception:
            return False
    
    async def navigate_to_pdp(self, pdp_url: str) -> bool:
        """Navigate to PDP page"""
        try:
            await self.page.goto(pdp_url, wait_until='domcontentloaded', timeout=10000)
            await handle_cookie_banner(self.page)
            return True
        except Exception:
            return False
    
    async def add_to_cart(self) -> bool:
        """Click add to cart button on PDP"""
        # Wait for page to be ready first (reduced timeout)
        try:
            await self.page.wait_for_load_state('domcontentloaded', timeout=5000)
        except Exception:
            pass
        
        add_to_cart_selectors = [
            'button:has-text("Forudbestil")',  # Pre-order button for humac.dk
            'button:has-text("Læg i kurv")',
            'button:has-text("Tilføj til kurv")',
            'button:has-text("Add to cart")',
            'button[class*="add-to-cart"]',
            'button[class*="addToCart"]',
            'button[class*="buy"]',
            'button[class*="cart"]',
            '[data-add-to-cart]',
            'button:has-text("Køb")',
            'button:has-text("Buy")',
            '[id*="add-to-cart"]',
            '[id*="buy"]',
            'a:has-text("Læg i kurv")',
            'a:has-text("Forudbestil")',
            'a[href*="cart"]'
        ]
        
        for selector in add_to_cart_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=3000, state='visible')
                if element:
                    # Scroll into view
                    await element.scroll_into_view_if_needed()
                    await self.page.wait_for_timeout(200)
                    # Click the element
                    await element.click()
                    # Wait for cart update (reduced)
                    await self.page.wait_for_timeout(1500)
                    # Verify click was successful (check for cart update or success message)
                    return True
            except Exception as e:
                continue
        
        return False
    
    async def navigate_to_cart(self, base_url: str) -> bool:
        """Navigate to cart page"""
        try:
            cart_url = f"{base_url.rstrip('/')}/cart"
            await self.page.goto(cart_url, wait_until='domcontentloaded', timeout=10000)
            await handle_cookie_banner(self.page)
            return True
        except Exception:
            return False
    
    async def navigate_to_checkout(self) -> Tuple[bool, Optional[str]]:
        """
        Click checkout button and navigate to checkout
        
        Returns:
            Tuple of (success, error_message)
        """
        checkout_selectors = [
            'button[class*="checkout"]',
            'a[class*="checkout"]',
            'button:has-text("Checkout")',
            'button:has-text("Til kassen")',
            'button:has-text("Gå til kassen")',
            'a:has-text("Checkout")',
            'a:has-text("Til kassen")',
            '[data-checkout]',
            '[id*="checkout"]'
        ]
        
        for selector in checkout_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=5000, state='visible')
                if element:
                    await element.click()
                    # Reduced wait time
                    try:
                        await self.page.wait_for_load_state('domcontentloaded', timeout=5000)
                    except Exception:
                        pass
                    await handle_cookie_banner(self.page)
                    return True, None
            except Exception as e:
                continue
        
        # Check if login is required
        login_indicators = [
            'input[type="email"]',
            'input[name*="email"]',
            'button:has-text("Login")',
            'button:has-text("Log ind")'
        ]
        
        for indicator in login_indicators:
            try:
                if await self.page.query_selector(indicator):
                    return False, "Login required"
            except Exception:
                continue
        
        return False, "Checkout button not found"
    
    async def wait_for_page_ready(
        self,
        selectors: List[str] = None,
        fallback_keywords: List[str] = None,
        timeout: int = 5000
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Wait for page to be ready
        Strategy: domcontentloaded + selector wait + keyword fallback (optimized for speed)
        """
        try:
            # Wait for DOM content loaded (faster than networkidle)
            await self.page.wait_for_load_state('domcontentloaded', timeout=min(timeout, 5000))
        except Exception:
            pass
        
        # Try selectors (reduced timeout)
        if selectors:
            for selector in selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000, state='visible')
                    return True, selector, None
                except Exception:
                    continue
        
        # Fallback to keyword search
        if fallback_keywords:
            try:
                page_text = await self.page.text_content()
                page_text_lower = page_text.lower() if page_text else ""
                for keyword in fallback_keywords:
                    if keyword.lower() in page_text_lower:
                        return True, None, keyword
            except Exception:
                pass
        
        return False, None, None
