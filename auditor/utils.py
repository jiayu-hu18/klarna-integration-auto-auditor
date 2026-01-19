"""
Utility functions for auditor
"""
import re
from typing import Optional, Tuple, Dict
from playwright.async_api import Page, ElementHandle, Frame


async def handle_cookie_banner(page: Page) -> None:
    """
    Try to handle cookie banner (click Accept/OK)
    Non-blocking: failures are ignored
    """
    cookie_selectors = [
        'button[class*="accept"]',
        'button[class*="cookie"]',
        'button[id*="accept"]',
        '#cookie-accept',
        '.cookie-accept',
        'button:has-text("Accept")',
        'button:has-text("OK")',
        'button:has-text("Allow all")',
        'button:has-text("Accepter")',
        'button:has-text("Godkend")',
        '[data-testid*="accept"]',
        '[data-testid*="cookie"]'
    ]
    
    for selector in cookie_selectors:
        try:
            element = await page.query_selector(selector)
            if element and await element.is_visible():
                await element.click(timeout=1000)
                await page.wait_for_timeout(200)  # Minimal wait for banner to disappear
                return
        except Exception:
            continue


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
