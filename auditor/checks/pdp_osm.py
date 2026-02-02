"""
Check 2: PDP_OSM
"""
import asyncio
from datetime import datetime
from typing import Tuple, List, Optional, Any
from playwright.async_api import Page, Locator
from auditor.navigator import Navigator, PRODUCT_SCOPE_SELECTORS
from auditor.screenshot import ScreenshotManager
from auditor.report import CheckResult, Evidence
from auditor.utils import find_element_in_frames

# Product scope for PDP: main, product containers, article (jula.se and others)
PDP_SCOPE_SELECTORS = list(PRODUCT_SCOPE_SELECTORS) + ["article", "[class*='product']", "[class*='Product']", "[class*='pdp']"]


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
            
            pdp_url = await navigator.navigate_to_pdp(pdp_url)
            if not pdp_url:
                return CheckResult(
                    check_id=self.CHECK_ID,
                    status="FAIL",
                    evidence=Evidence(),
                    timestamp=datetime.now().isoformat() + "Z",
                    error_reason="PDP navigation failed"
                )

            await navigator.clear_overlays("pdp-after-nav")
            await page.wait_for_timeout(1000)
            print("[DEBUG] PDP_OSM: checking for Klarna OSM within product scope ...")

            # Wait for PDP to settle, then capture full-page screenshot
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass
            try:
                await page.wait_for_selector(
                    "button:has-text('Læg i kurv'), button:has-text('Add to cart'), [data-product-id]",
                    timeout=4000,
                )
            except Exception:
                pass
            await navigator.clear_overlays("pdp-before-detect")
            await navigator.clear_overlays("pdp-before-screenshot")
            page_full_path = screenshot_manager._generate_path("pdp_full")
            await page.screenshot(path=page_full_path, full_page=True)

            product_scope = await self._get_product_scope(page)
            # 1) Check for Klarna iframe in product scope (strong evidence)
            iframe_el = await self._find_klarna_iframe_in_scope(page, product_scope)
            if iframe_el:
                await iframe_el.scroll_into_view_if_needed()
                await page.wait_for_timeout(300)
                element_path = screenshot_manager._generate_path("pdp_osm_element")
                await iframe_el.screenshot(path=element_path)
                print("[DEBUG] PDP_OSM: Klarna iframe found in product scope")
                return CheckResult(
                    check_id=self.CHECK_ID,
                    status="PASS",
                    evidence=Evidence(
                        screenshot_path=page_full_path,
                        page_screenshot_path=page_full_path,
                        element_screenshot_path=element_path,
                        matched_text="Klarna iframe"
                    ),
                    timestamp=datetime.now().isoformat() + "Z",
                    error_reason=None
                )

            locator = product_scope.locator(":text-matches('Klarna', 'i')")
            count = await locator.count()
            visible = []
            for i in range(count):
                el = locator.nth(i)
                if await el.is_visible():
                    visible.append(el)
            
            if not visible:
                # Fallback: full-page Klarna search -> WARN if found
                full_klarna = page.locator(":text-matches('Klarna', 'i')").first
                if await full_klarna.count() > 0 and await full_klarna.is_visible():
                    text_snippet = (await full_klarna.inner_text() or "").strip().replace("\n", " ")[:200]
                    await full_klarna.scroll_into_view_if_needed()
                    await page.wait_for_timeout(300)
                    element_path = screenshot_manager._generate_path("pdp_osm_element")
                    await full_klarna.screenshot(path=element_path)
                    print("[DEBUG] PDP_OSM: Klarna found outside product scope (WARN)")
                    return CheckResult(
                        check_id=self.CHECK_ID,
                        status="WARN",
                        evidence=Evidence(
                            screenshot_path=page_full_path,
                            page_screenshot_path=page_full_path,
                            element_screenshot_path=element_path,
                            matched_text=text_snippet
                        ),
                        timestamp=datetime.now().isoformat() + "Z",
                        error_reason="Klarna found on page but outside product scope"
                    )
                print("[DEBUG] PDP_OSM: no visible Klarna element found in product scope")
                return CheckResult(
                    check_id=self.CHECK_ID,
                    status="FAIL",
                    evidence=Evidence(
                        screenshot_path=page_full_path,
                        page_screenshot_path=page_full_path
                    ),
                    timestamp=datetime.now().isoformat() + "Z",
                    error_reason="No visible Klarna OSM in product scope"
                )
            
            osm_el = visible[0]
            text_snippet = (await osm_el.inner_text() or "").strip().replace("\n", " ")[:200]
            print(f"[DEBUG] PDP_OSM: using element text snippet: {text_snippet[:80]}")
            await osm_el.scroll_into_view_if_needed()
            await page.wait_for_timeout(300)
            element_path = screenshot_manager._generate_path("pdp_osm_element")
            await osm_el.screenshot(path=element_path)

            status = "PASS"
            error_reason = None
            evidence = Evidence(
                screenshot_path=page_full_path,
                page_screenshot_path=page_full_path,
                element_screenshot_path=element_path,
                matched_text=text_snippet
            )

            print(f"[{self.CHECK_ID}] {status} - Full page: {page_full_path}, Element: {element_path}")
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
    
    async def _get_product_scope(self, page: Page) -> Locator:
        """Resolve first available product scope container."""
        for sel in PDP_SCOPE_SELECTORS:
            try:
                loc = page.locator(sel)
                if await loc.count() > 0:
                    return loc.first
            except Exception:
                continue
        return page.locator("body").first
    
    async def _find_klarna_iframe_in_scope(self, page: Page, scope: Locator) -> Optional[Any]:
        """Return first visible iframe with src containing 'klarna' within scope."""
        try:
            iframes = scope.locator("iframe[src*='klarna' i]")
            n = await iframes.count()
            for i in range(n):
                el = iframes.nth(i)
                if await el.is_visible():
                    return el
        except Exception:
            pass
        return None
    
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
    
    async def detect_osm_keywords(self, page: Page) -> Tuple[str, List[str], Optional[str], Optional[Any]]:
        """
        Detect OSM with tiered evidence:
        - Strong: iframe or DOM container with klarna
        - Medium: network request with klarna/klarnacdn
        - Weak: text fallback (not used as sole PASS evidence)
        
        Returns: (evidence_level, matched_keywords, network_match, klarna_element)
        """
        matched_keywords = []
        network_match = None
        klarna_element = None
        
        # Minimal wait for OSM to load
        await page.wait_for_timeout(1000)
        
        # STRONG EVIDENCE: Check iframes and DOM containers with klarna
        klarna_selectors = [
            'iframe[src*="klarna"]',
            '[class*="klarna"]',
            '[id*="klarna"]',
            '[data-klarna]',
            '[class*="osm"]',
            '[id*="osm"]'
        ]
        
        widget_found = False
        for selector in klarna_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    widget_found = True
                    # Check iframe content
                    if await element.evaluate('el => el.tagName.toLowerCase()') == 'iframe':
                        try:
                            frame = await element.content_frame()
                            if frame:
                                frame_text = await frame.text_content()
                                frame_text_lower = frame_text.lower() if frame_text else ""
                                for keyword in self.KEYWORDS:
                                    if keyword.lower() in frame_text_lower and keyword not in matched_keywords:
                                        matched_keywords.append(keyword)
                                if matched_keywords:
                                    print("[DEBUG] STRONG evidence: Found Klarna in iframe")
                                    return "strong", matched_keywords, None, element
                        except Exception:
                            pass
                    else:
                        # Regular DOM container
                        element_text = await element.inner_text()
                        element_text_lower = element_text.lower() if element_text else ""
                        for keyword in self.KEYWORDS:
                            if keyword.lower() in element_text_lower and keyword not in matched_keywords:
                                matched_keywords.append(keyword)
                        if matched_keywords:
                            print("[DEBUG] STRONG evidence: Found Klarna in DOM container")
                            return "strong", matched_keywords, None, element
            except Exception:
                continue
        
        # MEDIUM EVIDENCE: Check network requests (check page source for klarnacdn)
        try:
            page_content = await page.content()
            if 'klarnacdn' in page_content.lower() or 'cdn.klarna' in page_content.lower():
                network_match = "klarnacdn found in page source"
                return "medium", matched_keywords, network_match, None
        except Exception:
            pass
        
        # WEAK EVIDENCE: Text fallback - search Klarna text ONLY inside main element
        try:
            # Search only in main element
            main = page.locator("main").first
            if await main.is_visible(timeout=2000):
                hit = main.locator(":text-matches('Klarna','i')").first
                if await hit.is_visible(timeout=2000):
                    klarna_element = await hit.element_handle()
                    matched_keywords.append("Klarna")
                    print("[DEBUG] Found Klarna text in main element (weak evidence)")
        except Exception:
            pass
            
            # Also check page text
            page_text = await page.text_content()
            page_text_lower = page_text.lower() if page_text else ""
            
            for keyword in self.KEYWORDS:
                if keyword.lower() in page_text_lower and keyword not in matched_keywords:
                    matched_keywords.append(keyword)
        except Exception:
            pass
        
        # Check iframes for text (weak evidence)
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
        
        if matched_keywords:
            return "weak", matched_keywords, network_match, klarna_element
        
        return "none", [], network_match, None
