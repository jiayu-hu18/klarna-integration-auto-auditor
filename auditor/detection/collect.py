"""
Lightweight evidence collection for detection. No scroll, no overlay handling, no footer.
Only homepage; domcontentloaded + short wait; collect scripts, cookies, globals, network (during navigation).
"""
import asyncio
from typing import Dict, Any, List, Set
from playwright.async_api import Page

# Wait after domcontentloaded (seconds)
SIGNALS_WAIT_AFTER_LOAD = 1.5
MAX_NETWORK_REQUESTS = 200
MAX_SCRIPT_SRCS = 500
MAX_LINK_HREFS = 300


async def collect_page_signals(
    page: Page,
    wait_after_load: float = SIGNALS_WAIT_AFTER_LOAD,
) -> Dict[str, Any]:
    """
    Collect signals from current page (assume already navigated to target URL).
    - final_url, script_srcs, link_hrefs (sample), cookies, global_vars_presence, network_requests_seen.
    Network listener should be attached before goto; we don't do goto here (caller does).
    """
    signals: Dict[str, Any] = {
        "final_url": page.url,
        "script_srcs": [],
        "link_hrefs": [],
        "cookies": [],
        "global_vars_presence": {},
        "network_requests_seen": [],
    }
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=10000)
    except Exception:
        pass
    await asyncio.sleep(wait_after_load)

    # Script srcs
    try:
        srcs = await page.evaluate(
            """() => Array.from(document.scripts).map(s => s.src).filter(Boolean).slice(0, %d)"""
            % MAX_SCRIPT_SRCS
        )
        if isinstance(srcs, list):
            signals["script_srcs"] = srcs
    except Exception:
        pass

    # Link hrefs (sample)
    try:
        hrefs = await page.evaluate(
            """() => Array.from(document.querySelectorAll('link[href], a[href]'))
            .map(el => el.href || el.getAttribute('href')).filter(Boolean).slice(0, %d)"""
            % MAX_LINK_HREFS
        )
        if isinstance(hrefs, list):
            signals["link_hrefs"] = hrefs
    except Exception:
        pass

    # Cookies (from context)
    try:
        context = page.context
        cookies = await context.cookies()
        signals["cookies"] = [{"name": c.get("name"), "domain": c.get("domain")} for c in (cookies or [])]
    except Exception:
        pass

    # Global vars (presence only)
    try:
        presence = await page.evaluate(
            """() => ({
                Shopify: typeof window.Shopify !== 'undefined',
                Stripe: typeof window.Stripe !== 'undefined',
                AdyenCheckout: typeof window.AdyenCheckout !== 'undefined',
            })"""
        )
        if isinstance(presence, dict):
            signals["global_vars_presence"] = presence
    except Exception:
        pass

    signals["final_url"] = page.url
    return signals


def attach_network_collector(page: Page, max_urls: int = MAX_NETWORK_REQUESTS) -> List[str]:
    """
    Attach request listener to page; returns a list that will be appended to. Call before goto.
    After goto + collect_page_signals, the list holds request URLs (deduped, up to max_urls).
    """
    seen: Set[str] = set()
    urls: List[str] = []

    def on_request(req):
        try:
            u = req.url
            if u not in seen and len(urls) < max_urls:
                seen.add(u)
                urls.append(u)
        except Exception:
            pass

    page.on("request", on_request)
    return urls
