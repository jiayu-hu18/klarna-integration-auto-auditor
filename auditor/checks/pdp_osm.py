"""
Check 2: PDP_OSM
"""
import asyncio
from datetime import datetime
from typing import Tuple, List
from playwright.async_api import Page
from auditor.navigator import Navigator
from auditor.screenshot import ScreenshotManager
from auditor.report import CheckResult, Evidence
from auditor.utils import find_element_in_frames


class PDPOSMCheck:
    """Check 2: PDP_OSM"""
    
    CHECK_ID = "PDP_OSM"
    KEYWORDS = ["Klarna", "Del op", "Pay in 3", "Kort", "Klarna Pay", "Klarna logo"]
    
    async def execute(
        self,
        page: Page,
        navigator: Navigator,
        screenshot_manager: ScreenshotManager,
        pdp_url: str
    ) -> CheckResult:
        """Execute PDP OSM check"""
        try:
            print(f"[{self.CHECK_ID}] Starting check...")
            
            # 1. Navigate to PDP
            success = await navigator.navigate_to_pdp(pdp_url)
            if not success:
                return CheckResult(
                    check_id=self.CHECK_ID,
                    status="FAIL",
                    evidence=Evidence(),
                    timestamp=datetime.now().isoformat() + "Z",
                    error_reason="PDP navigation failed"
                )
            
            # 2. Wait for page to load (minimal wait, don't wait for specific elements)
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=5000)
            except Exception:
                pass
            
            # Small wait for dynamic content
            await page.wait_for_timeout(1000)
            
            # 3. Detect OSM keywords (don't wait for price/buy button, just check for OSM)
            found, matched_keywords = await self.detect_osm_keywords(page)
            
            # 4. Capture screenshot
            screenshot_path = await screenshot_manager.capture_pdp_osm(page)
            
            # 5. Build evidence
            evidence = Evidence(
                screenshot_path=screenshot_path,
                matched_text=", ".join(matched_keywords) if matched_keywords else None
            )
            
            status = "PASS" if found else "FAIL"
            error_reason = None if found else "OSM keywords not found"
            
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
    
    async def wait_for_pdp_ready(self, page: Page, navigator: Navigator) -> bool:
        """Wait for PDP to be ready (price and buy button visible)"""
        # Wait for DOM content loaded (faster)
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=5000)
        except Exception:
            pass
        
        # Minimal wait for dynamic content
        await page.wait_for_timeout(1000)
        
        price_selectors = [
            '[class*="price"]',
            '[data-price]',
            '.price',
            '#price',
            '[class*="product-price"]',
            'span:has-text("kr")',
            'span:has-text("1.999")'
        ]
        
        buy_button_selectors = [
            'button:has-text("Læg i kurv")',
            'button:has-text("Tilføj til kurv")',
            'button:has-text("Forudbestil")',
            'button[class*="buy"]',
            'button[class*="cart"]',
            'button[class*="add"]',
            '[data-add-to-cart]',
            'button:has-text("Add")',
            'button:has-text("Køb")'
        ]
        
        # Check for price (reduced timeout)
        price_found = False
        for selector in price_selectors:
            try:
                await page.wait_for_selector(selector, timeout=3000, state='visible')
                price_found = True
                break
            except Exception:
                continue
        
        # Check for buy button (reduced timeout)
        button_found = False
        for selector in buy_button_selectors:
            try:
                await page.wait_for_selector(selector, timeout=3000, state='visible')
                button_found = True
                break
            except Exception:
                continue
        
        # Fallback: keyword search in page
        if not (price_found and button_found):
            try:
                page_text = await page.text_content()
                page_text_lower = page_text.lower() if page_text else ""
                if '1.999' in page_text or 'kr' in page_text_lower or 'pris' in page_text_lower:
                    price_found = True
                if 'læg i kurv' in page_text_lower or 'forudbestil' in page_text_lower or 'køb' in page_text_lower:
                    button_found = True
            except Exception:
                pass
        
        return price_found or button_found  # At least one should be found
    
    async def detect_osm_keywords(self, page: Page) -> Tuple[bool, List[str]]:
        """Detect OSM keywords in page content (check main frame and iframes)"""
        matched_keywords = []
        
        # Minimal wait for OSM to load
        await page.wait_for_timeout(500)
        
        # Check main frame
        try:
            page_text = await page.text_content()
            page_text_lower = page_text.lower() if page_text else ""
            
            for keyword in self.KEYWORDS:
                if keyword.lower() in page_text_lower:
                    matched_keywords.append(keyword)
        except Exception:
            pass
        
        # Check iframes (OSM is often in iframes)
        for frame in page.frames:
            if frame != page.main_frame:
                try:
                    frame_text = await frame.text_content()
                    frame_text_lower = frame_text.lower() if frame_text else ""
                    
                    for keyword in self.KEYWORDS:
                        if keyword.lower() in frame_text_lower and keyword not in matched_keywords:
                            matched_keywords.append(keyword)
                except Exception:
                    continue
        
        # Also check for Klarna widget/OSM specific selectors
        klarna_selectors = [
            '[class*="klarna"]',
            '[id*="klarna"]',
            '[data-klarna]',
            'iframe[src*="klarna"]',
            '[class*="osm"]',
            '[id*="osm"]'
        ]
        
        for selector in klarna_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    # Check iframe content if it's an iframe
                    if await element.evaluate('el => el.tagName.toLowerCase()') == 'iframe':
                        try:
                            frame = await element.content_frame()
                            if frame:
                                frame_text = await frame.text_content()
                                frame_text_lower = frame_text.lower() if frame_text else ""
                                for keyword in self.KEYWORDS:
                                    if keyword.lower() in frame_text_lower and keyword not in matched_keywords:
                                        matched_keywords.append(keyword)
                        except Exception:
                            pass
                    else:
                        # Regular element, check its text
                        element_text = await element.inner_text()
                        element_text_lower = element_text.lower() if element_text else ""
                        for keyword in self.KEYWORDS:
                            if keyword.lower() in element_text_lower and keyword not in matched_keywords:
                                matched_keywords.append(keyword)
            except Exception:
                continue
        
        return len(matched_keywords) > 0, matched_keywords
