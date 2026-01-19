"""
Check 1: FOOTER_KLARNA_LOGO
"""
from datetime import datetime
from typing import Tuple, Optional
from playwright.async_api import Page, ElementHandle
from auditor.navigator import Navigator
from auditor.screenshot import ScreenshotManager
from auditor.report import CheckResult, Evidence
from auditor.utils import find_element_in_frames, get_element_snippet_and_path


class FooterKlarnaLogoCheck:
    """Check 1: FOOTER_KLARNA_LOGO"""
    
    CHECK_ID = "FOOTER_KLARNA_LOGO"
    
    async def execute(
        self,
        page: Page,
        navigator: Navigator,
        screenshot_manager: ScreenshotManager,
        home_url: str
    ) -> CheckResult:
        """Execute footer Klarna logo check"""
        try:
            print(f"[{self.CHECK_ID}] Starting check...")
            
            # 1. Navigate to HOME
            success = await navigator.navigate_to_home(home_url)
            if not success:
                return CheckResult(
                    check_id=self.CHECK_ID,
                    status="FAIL",
                    evidence=Evidence(),
                    timestamp=datetime.now().isoformat() + "Z",
                    error_reason="Navigation to HOME failed"
                )
            
            # 2. Wait for page ready
            ready, selector, keyword = await navigator.wait_for_page_ready(
                selectors=['footer', '[class*="footer"]', '[id*="footer"]'],
                timeout=10000
            )
            
            # 3. Find footer element
            footer = await self.find_footer_element(page)
            
            # 4. Detect Klarna in footer
            found, matched_selector, matched_text = await self.detect_klarna_in_footer(page, footer)
            
            # 5. Capture screenshot
            screenshot_path = await screenshot_manager.capture_footer(page, footer)
            
            # 6. Build evidence
            evidence = Evidence(
                screenshot_path=screenshot_path,
                matched_selector=matched_selector,
                matched_text=matched_text
            )
            
            status = "PASS" if found else "FAIL"
            error_reason = None if found else "Klarna logo not found in footer"
            
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
    
    async def find_footer_element(self, page: Page) -> Optional[ElementHandle]:
        """Find footer element (check main frame and iframes)"""
        footer_selectors = ['footer', '[class*="footer"]', '[id*="footer"]']
        
        for selector in footer_selectors:
            footer, frame = await find_element_in_frames(page, selector)
            if footer:
                return footer
        
        return None
    
    async def detect_klarna_in_footer(
        self,
        page: Page,
        footer: Optional[ElementHandle]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Detect Klarna logo in footer"""
        # Check images in footer
        img_selectors = [
            'footer img[src*="klarna" i]',
            'footer img[alt*="klarna" i]',
            '[class*="footer"] img[src*="klarna" i]',
            '[class*="footer"] img[alt*="klarna" i]'
        ]
        
        for selector in img_selectors:
            try:
                img, frame = await find_element_in_frames(page, selector)
                if img:
                    # Get element info
                    info = await get_element_snippet_and_path(page, img)
                    return True, info['path'], None
            except Exception:
                continue
        
        # Check text in footer
        if footer:
            try:
                footer_text = await footer.inner_text()
                footer_text_lower = footer_text.lower()
                if 'klarna' in footer_text_lower:
                    return True, None, "Klarna found in footer text"
            except Exception:
                pass
        
        # Check page source
        try:
            page_source = await page.content()
            page_source_lower = page_source.lower()
            if 'klarna' in page_source_lower:
                # Try to find the specific location
                footer_section = page_source_lower.split('footer')[0] if 'footer' in page_source_lower else page_source_lower
                if 'klarna' in footer_section:
                    return True, None, "Klarna found in page source"
        except Exception:
            pass
        
        return False, None, None
