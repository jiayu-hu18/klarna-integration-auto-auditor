"""
Utility functions for auditor
"""
import asyncio
import re
import logging
from typing import Optional, Tuple, Dict, List
from playwright.async_api import Page, ElementHandle, Frame

log = logging.getLogger("auditor.utils")


async def handle_cookie_banner(page: Page) -> bool:
    """
    Try to handle cookie banner (click Accept). Retry up to 8 times with 500ms between rounds.
    Returns True if a button was clicked, False otherwise.
    """
    accept_texts = [
        "Acceptera alla cookies",
        "Acceptera alla",
        "Acceptera",
        "Tillåt alla",
        "Tillåt",
        "Accept all",
        "Accept",
    ]
    for _ in range(8):
        await page.wait_for_timeout(500)
        for text in accept_texts:
            try:
                btn = page.get_by_role("button", name=re.compile(re.escape(text), re.I)).first
                if await btn.is_visible(timeout=300):
                    actual = (await btn.inner_text() or "").strip() or text
                    await btn.scroll_into_view_if_needed()
                    await btn.click(force=True, timeout=1000)
                    print(f"[DEBUG] Cookie action: clicked '{actual}'")
                    await page.wait_for_timeout(800)
                    return True
            except Exception:
                continue
    print("[DEBUG] No cookie modal found")
    return False


async def get_element_snippet_and_path(
    page: Page,
    element: ElementHandle
) -> Dict[str, str]:
    """
    Get DOM snippet (innerHTML) and selector path (xpath/CSS path)
    """
    try:
        # Get snippet
        snippet = await element.inner_html()
        
        # Get xpath
        xpath = await page.evaluate("""
            (element) => {
                function getXPath(element) {
                    if (element.id !== '') return '//*[@id="' + element.id + '"]';
                    if (element === document.body) return '/html/body';
                    let ix = 0;
                    const siblings = element.parentNode.childNodes;
                    for (let i = 0; i < siblings.length; i++) {
                        const sibling = siblings[i];
                        if (sibling === element) {
                            return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                        }
                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) ix++;
                    }
                }
                return getXPath(element);
            }
        """, element)
        
        # Get CSS path (simplified)
        css_path = await page.evaluate("""
            (element) => {
                const path = [];
                while (element && element.nodeType === 1) {
                    let selector = element.tagName.toLowerCase();
                    if (element.id) {
                        selector += '#' + element.id;
                        path.unshift(selector);
                        break;
                    } else {
                        let sibling = element;
                        let nth = 1;
                        while (sibling.previousElementSibling) {
                            sibling = sibling.previousElementSibling;
                            if (sibling.tagName === element.tagName) nth++;
                        }
                        if (nth !== 1) selector += ':nth-of-type(' + nth + ')';
                    }
                    path.unshift(selector);
                    element = element.parentElement;
                }
                return path.join(' > ');
            }
        """, element)
        
        return {
            'snippet': snippet[:500] if len(snippet) > 500 else snippet,  # Limit length
            'path': css_path or xpath
        }
    except Exception:
        return {'snippet': '', 'path': ''}


async def find_element_in_frames(
    page: Page,
    selector: str
) -> Tuple[Optional[ElementHandle], Optional[Frame]]:
    """
    Find element, checking iframe frames if not found in main frame
    """
    # Try main frame first
    try:
        element = await page.query_selector(selector)
        if element:
            return element, page.main_frame
    except Exception:
        pass
    
    # Check all frames
    for frame in page.frames:
        if frame != page.main_frame:
            try:
                element = await frame.query_selector(selector)
                if element:
                    return element, frame
            except Exception:
                continue
    
    return None, None


def detect_country_from_url(url: str) -> Optional[str]:
    """
    Detect country code from URL
    """
    country_map = {
        '.dk': 'DK',
        '.se': 'SE',
        '.no': 'NO',
        '.fi': 'FI',
        '.de': 'DE',
        '.nl': 'NL'
    }
    
    for domain, country in country_map.items():
        if domain in url.lower():
            return country
    
    return None


# ---------- overlay / widget helpers ----------


async def try_close_common_overlays(page: Page, max_clicks_per_selector: int = 3) -> List[str]:
    """
    Try to click common overlay close/dismiss buttons. Returns list of selectors that were clicked.
    Safe to call repeatedly.
    """
    close_selectors = [
        'button[aria-label*="close"]',
        'button[aria-label*="Close"]',
        'button:has-text("Close")',
        'button:has-text("Stäng")',
        'button:has-text("Avvisa")',
        'button:has-text("Avvisa alla")',
        'button:has-text("Dismiss")',
        'button:has-text("Avbryt")',
        'button[class*="close"]',
        '.widget-close',
        '.chat-close',
        '.intercom-launcher',
        '.intercom-container .dismiss',
        '.crisp-client .crisp-client-close',
        '.tawk-button',
        '.lc-widget__close',
        '.livechat_pop_up_close_button',
        '.fb-customer-chat',
        '.chat-widget',
        '.help-widget',
        '.wc-floating',
        '.widget-toggle',
    ]
    clicked = []
    for sel in close_selectors:
        try:
            locator = page.locator(sel)
            count = await locator.count()
            if not count:
                continue
            for i in range(min(max_clicks_per_selector, count)):
                el = locator.nth(i)
                try:
                    if await el.is_visible():
                        await el.click(timeout=1500)
                        clicked.append(sel)
                        await page.wait_for_timeout(220)
                except Exception:
                    try:
                        await el.evaluate("el => el.scrollIntoView()")
                        await el.click(timeout=1200)
                        clicked.append(sel)
                        await page.wait_for_timeout(180)
                    except Exception:
                        pass
        except Exception:
            pass
    if clicked:
        log.debug("try_close_common_overlays clicked: %s", clicked)
    return clicked


async def hide_high_zindex_overlays(page: Page, debug_prefix: Optional[str] = None) -> int:
    """
    Temporarily hide high z-index fixed/absolute elements that may cover the view
    (skip elements with footer/header in id or class). Returns number of elements hidden.
    If debug_prefix is set, saves before/after screenshots.
    """
    try:
        if debug_prefix:
            try:
                await page.screenshot(path=f"{debug_prefix}_before_overlays.png")
            except Exception:
                pass

        hide_script = r"""
        (() => {
          const hiddenIds = [];
          const nodes = Array.from(document.querySelectorAll('body *'));
          for (const n of nodes) {
            try {
              const s = window.getComputedStyle(n);
              if (!s) continue;
              const pos = s.position;
              if (!pos || (pos !== 'fixed' && pos !== 'sticky' && pos !== 'absolute')) continue;
              let z = 0;
              try { z = parseInt(s.zIndex) || 0; } catch(e){}
              const big = (n.clientHeight > window.innerHeight*0.25 || n.clientWidth > window.innerWidth*0.25);
              if (z >= 50 || big) {
                const id = (n.id||'').toLowerCase();
                const cls = (n.className||'').toLowerCase();
                if (id.includes('footer') || cls.includes('footer') || id.includes('header') || cls.includes('header')) continue;
                n.setAttribute('data-auditor-hidden','1');
                n.__auditor_old_display = n.style.display || '';
                n.style.display = 'none';
                hiddenIds.push(n);
              }
            } catch(e){}
          }
          return hiddenIds.length;
        })();
        """
        count = await page.evaluate(hide_script)
        await page.wait_for_timeout(250)
        if debug_prefix:
            try:
                await page.screenshot(path=f"{debug_prefix}_after_overlays.png")
            except Exception:
                pass
        log.debug("hide_high_zindex_overlays hid %s elements", count)
        return int(count or 0)
    except Exception:
        log.exception("hide_high_zindex_overlays failed")
        return 0


async def find_klarna_text_in_footer(page: Page) -> bool:
    """
    Check if footer (footer or [role=contentinfo]) contains 'klarna' (case-insensitive).
    Text fallback when image matching fails.
    """
    try:
        footer = page.locator("footer, [role=contentinfo]").first
        if await footer.count():
            text = (await footer.inner_text()).lower()
            if "klarna" in text:
                return True
        if await page.locator("text=/klarna/i").count():
            return True
    except Exception:
        pass
    return False
