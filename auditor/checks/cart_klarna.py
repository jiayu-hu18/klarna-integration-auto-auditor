"""
Check 3: CART_KLARNA
"""
from datetime import datetime
from typing import Tuple, Optional
from playwright.async_api import Page, ElementHandle
from auditor.navigator import Navigator
from auditor.screenshot import ScreenshotManager
from auditor.report import CheckResult, Evidence


class CartKlarnaCheck:
    """Check 3: CART_KLARNA"""
    
    CHECK_ID = "CART_KLARNA"
    
    async def execute(
        self,
        page: Page,
        navigator: Navigator,
        screenshot_manager: ScreenshotManager,
        base_url: str
    ) -> CheckResult:
        """Execute cart Klarna check"""
        try:
            print(f"[{self.CHECK_ID}] Starting check...")
            
            # 1. Ensure we're on PDP first (navigate if needed)
            current_url = navigator.page.url
            if 'produkter' not in current_url.lower():
                # Navigate to PDP first
                pdp_url = f"{base_url.rstrip('/')}/produkter/headphones/airpods-pro-3"
                await navigator.navigate_to_pdp(pdp_url)
                await navigator.page.wait_for_timeout(2000)
            
            # 2. Click add to cart
            success = await navigator.add_to_cart()
            if not success:
                # Try to navigate to cart anyway to see what's there
                await navigator.navigate_to_cart(base_url)
                screenshot_path = await screenshot_manager.capture_cart(navigator.page)
                return CheckResult(
                    check_id=self.CHECK_ID,
                    status="FAIL",
                    evidence=Evidence(screenshot_path=screenshot_path),
                    timestamp=datetime.now().isoformat() + "Z",
                    error_reason="Add to cart button not found or click failed"
                )
            
            # 3. Minimal wait to ensure cart is updated
            await navigator.page.wait_for_timeout(500)
            
            # 4. Navigate to cart
            success = await navigator.navigate_to_cart(base_url)
            if not success:
                return CheckResult(
                    check_id=self.CHECK_ID,
                    status="FAIL",
                    evidence=Evidence(),
                    timestamp=datetime.now().isoformat() + "Z",
                    error_reason="Cart navigation failed"
                )
            
            # 3. Wait for cart to load (reduced timeout)
            ready, selector, keyword = await navigator.wait_for_page_ready(
                selectors=['[class*="cart"]', '[id*="cart"]', '[class*="summary"]'],
                timeout=5000
            )
            
            # Check if cart is empty
            empty_indicators = [
                'text="Kurven er tom"',
                'text="Cart is empty"',
                'text="Din kurv er tom"',
                '[class*="empty"]',
                '[class*="no-items"]'
            ]
            
            cart_empty = False
            for indicator in empty_indicators:
                try:
                    if await page.query_selector(indicator):
                        cart_empty = True
                        break
                except Exception:
                    continue
            
            # Also check page text
            try:
                page_text = await page.text_content()
                if page_text:
                    page_text_lower = page_text.lower()
                    if 'kurven er tom' in page_text_lower or 'cart is empty' in page_text_lower or 'din kurv er tom' in page_text_lower:
                        cart_empty = True
            except Exception:
                pass
            
            if cart_empty:
                screenshot_path = await screenshot_manager.capture_cart(page)
                return CheckResult(
                    check_id=self.CHECK_ID,
                    status="FAIL",
                    evidence=Evidence(screenshot_path=screenshot_path),
                    timestamp=datetime.now().isoformat() + "Z",
                    error_reason="Cart is empty - product was not added to cart successfully"
                )
            
            # 4. Detect Klarna in cart
            found, matched_text = await self.detect_klarna_in_cart(page)
            
            # 5. Find cart summary area (optional)
            cart_summary = await self.find_cart_summary_area(page)
            
            # 6. Capture screenshot
            screenshot_path = await screenshot_manager.capture_cart(page, cart_summary)
            
            # 7. Build evidence
            evidence = Evidence(
                screenshot_path=screenshot_path,
                matched_text=matched_text
            )
            
            status = "PASS" if found else "FAIL"
            error_reason = None if found else "Klarna not found in cart"
            
            print(f"[{self.CHECK_ID}] {status} - Screenshot: {screenshot_path}")
            if error_reason:
                print(f"[{self.CHECK_ID}] Error: {error_reason}")
            
            return CheckResult(
                check_id=self.CHECK_ID,
                status=status,
                evidence=evidence,
                timestamp=datetime.now().isoformat() + "Z",
                error_reason=error_reason
            )
            
        except Exception as e:
            print(f"[{self.CHECK_ID}] Exception: {str(e)}")
            return CheckResult(
                check_id=self.CHECK_ID,
                status="FAIL",
                evidence=Evidence(),
                timestamp=datetime.now().isoformat() + "Z",
                error_reason=f"Exception: {str(e)}"
            )
    
    async def detect_klarna_in_cart(self, page: Page) -> Tuple[bool, Optional[str]]:
        """Detect Klarna keyword in cart page"""
        try:
            page_text = await page.text_content()
            page_text_lower = page_text.lower() if page_text else ""
            
            if 'klarna' in page_text_lower:
                # Find the context around "klarna"
                index = page_text_lower.find('klarna')
                start = max(0, index - 50)
                end = min(len(page_text), index + 50)
                context = page_text[start:end].strip()
                return True, context
        except Exception:
            pass
        
        return False, None
    
    async def find_cart_summary_area(self, page: Page) -> Optional[ElementHandle]:
        """Find cart summary area for screenshot"""
        cart_selectors = [
            '[class*="cart-summary"]',
            '[class*="cart-total"]',
            '[class*="cart-totals"]',
            '[id*="cart-summary"]',
            '.summary',
            '[class*="summary"]',
            '[class*="totals"]'
        ]
        
        for selector in cart_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    return element
            except Exception:
                continue
        
        return None
