"""
Screenshot management
"""
from pathlib import Path
from datetime import datetime
from playwright.async_api import Page, ElementHandle


class ScreenshotManager:
    """Manage screenshots for audit"""
    
    def __init__(self, out_dir: str, merchant: str = "humac.dk"):
        self.out_dir = Path(out_dir)
        self.merchant = merchant
        self.merchant_dir = self.out_dir / merchant
        self.merchant_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_path(self, page_type: str) -> str:
        """
        Generate screenshot path: {out_dir}/{merchant}/{page_type}_{yyyyMMdd_HHmmss}.png
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{page_type}_{timestamp}.png"
        return str(self.merchant_dir / filename)
    
    async def capture_footer(
        self,
        page: Page,
        footer_element: ElementHandle = None
    ) -> str:
        """Capture footer screenshot"""
        path = self._generate_path("footer")
        
        if footer_element:
            try:
                await footer_element.screenshot(path=path)
            except Exception:
                # Fallback to full page
                await page.screenshot(path=path, full_page=True)
        else:
            # Try to find footer and capture
            try:
                footer = await page.query_selector('footer')
                if footer:
                    await footer.screenshot(path=path)
                else:
                    await page.screenshot(path=path, full_page=True)
            except Exception:
                await page.screenshot(path=path, full_page=True)
        
        return path
    
    async def capture_pdp_osm(
        self,
        page: Page
    ) -> str:
        """Capture PDP OSM/price area screenshot"""
        path = self._generate_path("pdp_osm")
        
        # Try to capture price/OSM area
        try:
            # Look for price element
            price_selectors = ['.price', '[class*="price"]', '[data-price]', '#price']
            for selector in price_selectors:
                try:
                    price_element = await page.query_selector(selector)
                    if price_element:
                        # Get bounding box and expand to capture surrounding area
                        box = await price_element.bounding_box()
                        if box:
                            # Expand box to capture more area
                            expanded_box = {
                                'x': max(0, box['x'] - 100),
                                'y': max(0, box['y'] - 200),
                                'width': box['width'] + 200,
                                'height': box['height'] + 400
                            }
                            await page.screenshot(path=path, clip=expanded_box)
                            return path
                except Exception:
                    continue
        except Exception:
            pass
        
        # Fallback: capture viewport (not full page to focus on content)
        await page.screenshot(path=path)
        return path
    
    async def capture_cart(
        self,
        page: Page,
        cart_summary_element: ElementHandle = None
    ) -> str:
        """Capture cart screenshot"""
        path = self._generate_path("cart")
        
        if cart_summary_element:
            try:
                await cart_summary_element.screenshot(path=path)
                return path
            except Exception:
                pass
        
        # Try to find cart summary
        cart_selectors = [
            '[class*="cart-summary"]',
            '[class*="cart-total"]',
            '[class*="cart-totals"]',
            '[id*="cart-summary"]',
            '.summary',
            '[class*="summary"]'
        ]
        
        for selector in cart_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    await element.screenshot(path=path)
                    return path
            except Exception:
                continue
        
        # Fallback: full page
        await page.screenshot(path=path, full_page=True)
        return path
    
    async def capture_checkout_payment(
        self,
        page: Page,
        payment_methods_element: ElementHandle = None
    ) -> str:
        """Capture checkout payment methods screenshot"""
        path = self._generate_path("checkout_payment")
        
        if payment_methods_element:
            try:
                await payment_methods_element.screenshot(path=path)
                return path
            except Exception:
                pass
        
        # Try to find payment methods area
        payment_selectors = [
            '[class*="payment"]',
            '[id*="payment"]',
            '[data-payment]',
            '.payment-options',
            '.payment-methods'
        ]
        
        for selector in payment_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    await element.screenshot(path=path)
                    return path
            except Exception:
                continue
        
        # Fallback: full page
        await page.screenshot(path=path, full_page=True)
        return path
