"""
Page navigation logic
"""
import asyncio
import os
import random
import re
from typing import List, Tuple, Optional, Dict, Any
from urllib.parse import urlparse, urljoin
from playwright.async_api import Page
from auditor.utils import handle_cookie_banner, try_close_common_overlays, hide_high_zindex_overlays

# ATC regex patterns
ATC_INCLUDE = re.compile(r"(varukorg|kundvagn|lägg\s+i\s*(varukorg|kundvagn|varukorgen)|köp\b)", re.I)
ATC_EXCLUDE = re.compile(r"(klarna|delbetala|betal\s+senare|välj|färg|storlek|size)", re.I)
PRODUCT_SCOPE_SELECTORS = ["main", "[data-product]", ".product", ".pdp", "#product", ".product-detail", ".product-card", ".product-page"]

# PDP URL patterns: prefer product detail pages, exclude order/cart/checkout
CANDIDATE_HREF_SELECTORS = [
    "a[href*='/item/']",
    "a[href*='/product/']",
    "a[href*='/produkt/']",
    "a[href*='/products/']",
    "a[href*='/p/']",
]
EXCLUDE_PATTERNS = ["/p/order", "/p/cart", "/cart", "/order", "/checkout"]
# Good PDP path patterns (check in order; .co.uk before .com handled by length sort elsewhere)
GOOD_PATH_PATTERNS = ["/product/", "/item/", "/produkt/", "/vara/", "/p/itm", "/products/"]
BAD_PATH_PATTERNS = ["/order/", "/cart", "/checkout", "/p/order/"]
TILE_SELECTORS = [".product-card a", ".product-tile a", ".product-item a", "[data-product-id] a", ".product__link", ".result-item a", ".productItem a"]

# Shein: no /p/ structure; product URLs are domain + path (e.g. shein.se/Product-Name-p-123). Exclude login/social/policy.
SHEIN_EXCLUDE_PATTERNS = [
    "login", "signin", "sign-in", "facebook", "google", "apple", "register", "account",
    "cart", "checkout", "wishlist", "wish-list", "auth", "oauth", "callback",
    "policy", "privacy", "security", "terms", "help", "about", "contact", "faq",
    "risk", "action/limit", "limit?risk",  # Shein risk/verification pages
]
# Only links with -p- (product) or -g- (goods) are treated as product pages; avoids policy/article (-a-) pages
SHEIN_PRODUCT_LINK_PATTERNS = ["-p-", "-g-", "/detail/", "/product-detail/"]
SHEIN_TILE_SELECTORS = [
    "a[href*='-p-']",
    "a[href*='-g-']",
    "[class*='product'] a[href^='/']",
    "[class*='Product'] a[href^='/']",
    ".goods-item a",
    ".product-item a",
    "[class*='ProductCard'] a",
    "a[data-id]",
]


async def hide_known_overlays(page: Page) -> None:
    """Click close buttons and hide known overlays (chat, cookie bar, modals) so content is visible."""
    selectors_to_click = [
        "button[aria-label*='close']", "button[title*='close']", ".cookie-banner button:has-text('Accept')",
        "button:has-text('Acceptera')", "button:has-text('Accepter')", "button:has-text('Accept all')",
        ".newsletter .close", ".modal .close", ".cookie-modal button:has-text('Acceptera alla')",
    ]
    selectors_to_hide = [
        ".chat-widget", ".chatbox", ".live-support", ".floating-chat", ".intercom-launcher", "#sp-chat",
        ".cookie-consent", ".cookie-banner", ".subscription-modal", ".promo-popup",
    ]
    for sel in selectors_to_click:
        try:
            els = await page.query_selector_all(sel)
            for e in els:
                try:
                    await e.click(timeout=800)
                    await page.wait_for_timeout(200)
                except Exception:
                    try:
                        await page.evaluate("(el) => { if (el && el.style) el.style.display='none'; }", e)
                    except Exception:
                        pass
        except Exception:
            pass
    for sel in selectors_to_hide:
        try:
            await page.evaluate(
                """(s) => { document.querySelectorAll(s).forEach(e=>{ if(e&&e.style) e.style.display='none'; }); }""",
                sel,
            )
        except Exception:
            pass


async def scroll_to_bottom_until_stable(page: Page, max_attempts: int = 5, wait_ms: int = 800) -> bool:
    """Scroll to bottom repeatedly until scrollHeight is stable (for lazy-loaded footer). Returns True if stable."""
    prev_height = -1
    for i in range(max_attempts):
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        except Exception:
            break
        await page.wait_for_timeout(wait_ms + i * 200)
        try:
            height = await page.evaluate("document.body.scrollHeight")
            if height == prev_height:
                return True
            prev_height = height
        except Exception:
            break
    return False


async def dismiss_overlays(
    page: Page,
    *,
    rounds: int = 6,
    per_action_timeout_ms: int = 800,
    debug: bool = False,
) -> None:
    """
    Aggressively dismiss popups/overlays. Call this:
      - right after every navigation
      - before scrolling to footer
      - right before taking screenshots
      - after page reloads / route changes
    """
    host = ""
    try:
        host = (page.url or "").lower()
    except Exception:
        pass

    close_button_selectors: List[str] = [
        "button[aria-label='Close']",
        "button[aria-label='close']",
        "button[title='Close']",
        "button[title='close']",
        "button[aria-label*='close' i]",
        "button[title*='close' i]",
        "[data-testid*='close' i]",
        ".close",
        ".close-btn",
        ".closeButton",
        ".modal__close",
        ".overlay__close",
        ".newsletter-modal .close",
        ".popup-close",
        ".dialog-close",
        ".next-dialog-close",
        ".next-overlay-wrapper .next-dialog-close",
        "button[class*='close' i]",
    ]

    consent_texts = [
        "Accept all", "Accept All", "Accept",
        "Acceptera alla", "Acceptera", "Godkänn", "Tillåt alla",
        "Agree", "I agree", "OK",
        "Avvisa", "Reject", "Reject all", "Decline",
        "Cookie settings", "Cookie-inställningar",
        "Bekräfta", "Confirm", "Confirm my choices",
    ]

    notification_texts = [
        "Don't allow", "Dont allow", "Do not allow",
        "Not now", "No thanks", "Later",
        "Allow",
        "Tillåt inte", "Inte nu",
    ]

    overlay_containers = [
        "[role='dialog']",
        ".modal",
        ".popup",
        ".overlay",
        ".backdrop",
        ".mask",
        ".drawer",
        ".sheet",
        ".toast",
        ".notification",
        ".cookies",
        ".cookie",
        ".consent",
        ".next-overlay-wrapper",
        ".next-dialog",
        ".next-modal",
        "#_overlay_",
    ]

    async def _click_all_selectors(selectors: List[str]) -> None:
        for sel in selectors:
            try:
                loc = page.locator(sel)
                count = await loc.count()
                if count == 0:
                    continue
                for i in range(min(count, 8)):
                    try:
                        item = loc.nth(i)
                        if await item.is_visible():
                            await item.click(timeout=per_action_timeout_ms)
                            if debug:
                                print(f"[DEBUG] dismiss_overlays: clicked selector {sel} nth={i}")
                    except Exception:
                        pass
            except Exception:
                pass

    async def _click_by_text(texts: List[str], prefer_negative: bool = True) -> None:
        neg = []
        pos = []
        for t in texts:
            tl = t.lower()
            if any(k in tl for k in ["don't", "dont", "reject", "decline", "avvisa", "inte", "not now", "no thanks"]):
                neg.append(t)
            else:
                pos.append(t)
        ordered = neg + pos if prefer_negative else texts
        for t in ordered:
            try:
                btn = page.get_by_role("button", name=re.compile(re.escape(t), re.I))
                if await btn.count() > 0:
                    cnt = await btn.count()
                    for i in range(min(cnt, 6)):
                        try:
                            b = btn.nth(i)
                            if await b.is_visible():
                                await b.click(timeout=per_action_timeout_ms)
                                if debug:
                                    print(f"[DEBUG] dismiss_overlays: clicked button text '{t}' nth={i}")
                        except Exception:
                            pass
            except Exception:
                pass

    async def _js_hide_overlays() -> None:
        try:
            await page.evaluate(
                """(containers) => {
                    const sels = containers || [];
                    for (const s of sels) {
                        document.querySelectorAll(s).forEach(el => {
                            if (!el || el === document.body || el === document.documentElement) return;
                            el.style.setProperty('display','none','important');
                            el.style.setProperty('visibility','hidden','important');
                            el.style.setProperty('pointer-events','none','important');
                        });
                    }
                    document.documentElement.style.overflow = 'auto';
                    document.body.style.overflow = 'auto';
                    document.body.style.position = 'static';
                }""",
                overlay_containers,
            )
        except Exception:
            pass

    if "aliexpress" in host:
        try:
            x_candidates = page.locator(".next-dialog-close, .close, .close-btn")
            cnt = await x_candidates.count()
            for i in range(min(cnt, 8)):
                try:
                    el = x_candidates.nth(i)
                    if await el.is_visible():
                        await el.click(timeout=800)
                        if debug:
                            print("[DEBUG] dismiss_overlays: clicked AliExpress close nth=", i)
                except Exception:
                    pass
            for char in ["×", "✕"]:
                try:
                    loc = page.get_by_text(char, exact=True)
                    if await loc.count() > 0:
                        for i in range(min(await loc.count(), 4)):
                            try:
                                el = loc.nth(i)
                                if await el.is_visible():
                                    await el.click(timeout=800)
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass
        try:
            await page.evaluate("""
                () => {
                  const nodes = Array.from(document.querySelectorAll('[role="dialog"], .next-dialog, .next-overlay-wrapper'));
                  nodes.forEach(n => {
                    const t = (n.innerText || '').toLowerCase();
                    if (t.includes('free gift') || t.includes('press to get')) {
                      n.style.setProperty('display','none','important');
                      n.style.setProperty('pointer-events','none','important');
                    }
                  });
                }
            """)
        except Exception:
            pass

    for r in range(rounds):
        await _click_all_selectors(close_button_selectors)
        await _click_by_text(consent_texts, prefer_negative=False)
        await _click_by_text(notification_texts, prefer_negative=True)
        await _js_hide_overlays()
        await page.wait_for_timeout(250)
        try:
            dialogs = await page.locator("[role='dialog'], .next-overlay-wrapper, .modal, .overlay").count()
            if dialogs == 0:
                break
        except Exception:
            pass


async def click_by_js(element):
    """JS-safe click helper"""
    try:
        await element.evaluate("el => el.scrollIntoView({block:'center', inline:'center'})")
        await element.click(force=True)
        return True
    except Exception:
        try:
            await element.evaluate("el => el.click()")
            return True
        except Exception:
            try:
                box = await element.bounding_box()
                if box:
                    await element.page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                    await element.page.mouse.down()
                    await element.page.mouse.up()
                    return True
            except Exception:
                pass
    return False


async def handle_cookie_consent(page, timeout_ms: int = 3000):
    """Handle cookie consent modal"""
    await asyncio.sleep(0.3)
    texts_accept = ["Acceptera alla cookies", "Acceptera alla", "Acceptera", "Tillåt alla", "Tillåt", "Accept all", "Accept"]
    close_selectors = ["button[aria-label*='close']", "button[aria-label*='stäng']", ".cookie-close", ".consent-close", ".cc-close"]
    frames = [page] + list(page.frames)
    for f in frames:
        for t in texts_accept:
            try:
                loc = f.locator(f":text-matches('{re.escape(t)}','i')").first
                if await loc.count() and await loc.is_visible():
                    await click_by_js(loc)
                    print(f"[DEBUG] Cookie action: clicked '{t}'")
                    await asyncio.sleep(0.7)
                    return True
            except Exception:
                continue
        for sel in close_selectors:
            try:
                loc = f.locator(sel).first
                if await loc.count() and await loc.is_visible():
                    await click_by_js(loc)
                    print(f"[DEBUG] Cookie action: clicked close selector '{sel}'")
                    await asyncio.sleep(0.6)
                    return True
            except Exception:
                continue
    print("[DEBUG] No cookie modal found")
    return False


async def find_product_scope(page):
    """Find product scope container"""
    for sel in PRODUCT_SCOPE_SELECTORS:
        try:
            loc = page.locator(sel)
            if await loc.count() > 0:
                return loc.first
        except Exception:
            continue
    return page.locator("body").first


async def dump_ctas_in_scope(page, scope, max_items=80):
    """Dump visible CTAs in scope"""
    elems = scope.locator("button:visible, a:visible, [role='button']:visible")
    n = min(max_items, await elems.count())
    ctas = []
    for i in range(n):
        try:
            t = (await elems.nth(i).inner_text()).strip()
        except Exception:
            try:
                t = (await elems.nth(i).get_attribute("aria-label") or "") or ""
            except Exception:
                t = ""
        t = " ".join(t.split())
        if t:
            ctas.append((i, t))
    print("[DEBUG] === Visible CTAs in product scope (first %d) ===" % len(ctas))
    for idx, text in ctas:
        print(f"[DEBUG] {idx+1}. {text}")
    print("[DEBUG] =================================================")
    return ctas, elems


async def handle_post_atc_modals_helper(page, max_loops=3):
    """Handle post-ATC modals"""
    for attempt in range(1, max_loops+1):
        try:
            modal = page.locator("[role='dialog']:visible, .modal:visible, .c-modal:visible").first
            if await modal.count() == 0:
                modal = page
        except Exception:
            modal = page
        try:
            go_cart = modal.locator(":text-matches('gå\\s*(till|til|i)\\s*(varukorg|kundvagn)|go\\s+to\\s+cart','i')").first
            if await go_cart.count() and await go_cart.is_visible():
                await click_by_js(go_cart)
                print(f"[DEBUG] Modal step {attempt}: Clicked go-to-cart")
                try:
                    await page.wait_for_url(re.compile(r"/cart|/varukorg|/kundvagn"), timeout=10000)
                except Exception:
                    pass
                return True
        except Exception:
            pass
        try:
            no_thanks = modal.locator(":text-matches('nej\\s+tack|no\\s+thanks|skip|avbryt','i')").first
            if await no_thanks.count() and await no_thanks.is_visible():
                await click_by_js(no_thanks)
                print(f"[DEBUG] Modal step {attempt}: Clicked 'no thanks'")
                await asyncio.sleep(0.5)
                continue
        except Exception:
            pass
        try:
            cont = modal.locator(":text-matches('forts[aä]tt|fortsaet|continue|nästa','i')").first
            if await cont.count() and await cont.is_visible():
                await click_by_js(cont)
                print(f"[DEBUG] Modal step {attempt}: Clicked Continue")
                await asyncio.sleep(0.5)
                continue
        except Exception:
            pass
        break
    try:
        header_cart = page.locator("a[href*='/cart'], a[href*='varukorg'], a[href*='kundvagn'], button[aria-label*='cart']").first
        if await header_cart.count() and await header_cart.is_visible():
            await click_by_js(header_cart)
            print("[DEBUG] Clicked header cart fallback")
            try:
                await page.wait_for_url(re.compile(r"/cart|/varukorg|/kundvagn"), timeout=8000)
            except Exception:
                pass
            return True
    except Exception:
        pass
    return False


class Navigator:
    """Handle page navigation and flow"""
    
    def __init__(self, page: Page, headless: bool = True, home_url: str = ""):
        self.page = page
        self.headless = headless
        self.home_url = home_url or ""
    
    async def dismiss_cookie_banner(self) -> bool:
        """Try to click cookie consent button. Non-blocking: max ~4s."""
        texts = [
            "Acceptera alla cookies", "Acceptera alla", "Acceptera",
            "Tillåt alla", "Tillåt", "Accept all", "Accept",
        ]
        for attempt in range(8):
            for t in texts:
                try:
                    btn = self.page.get_by_role("button", name=re.compile(re.escape(t), re.I))
                    if await btn.count() > 0:
                        el = btn.first
                        if await el.is_visible():
                            await el.scroll_into_view_if_needed()
                            await el.click(force=True)
                            print(f"[DEBUG] Cookie action: clicked '{t}'")
                            await self.page.wait_for_timeout(800)
                            return True
                except Exception:
                    continue
            await self.page.wait_for_timeout(500)
        print("[DEBUG] No cookie modal found")
        return False
    
    async def scroll_to_bottom_until_stable(self, max_attempts: int = 5, wait_ms: int = 800) -> bool:
        """Scroll to bottom until scrollHeight is stable (for lazy-loaded footer). Returns True if stable."""
        return await scroll_to_bottom_until_stable(self.page, max_attempts, wait_ms)

    async def scroll_to_bottom_stable(self, max_rounds: int = 6) -> None:
        """Scroll to bottom until scrollHeight is stable for 2 rounds (for lazy/infinite-load footer)."""
        page = self.page
        last_h = 0
        stable = 0
        for i in range(max_rounds):
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            except Exception:
                pass
            await page.wait_for_timeout(700)
            try:
                h = await page.evaluate("document.body.scrollHeight")
            except Exception:
                h = last_h
            if h == last_h:
                stable += 1
            else:
                stable = 0
            last_h = h
            if stable >= 2:
                break

    async def scroll_to_bottom_stable_wheel(self, max_attempts: int = 8, inner_rolls: int = 5) -> None:
        """
        Stable scroll using mouse.wheel (handles infinite-load). Each attempt: roll wheel down inner_rolls times,
        wait 300ms; if scrollHeight unchanged for 2 consecutive attempts, stop.
        """
        page = self.page
        last_h = 0
        stable = 0
        for attempt in range(max_attempts):
            for _ in range(inner_rolls):
                try:
                    await page.mouse.wheel(0, 2000)
                except Exception:
                    pass
                await page.wait_for_timeout(300)
            try:
                h = await page.evaluate("document.body.scrollHeight")
            except Exception:
                h = last_h
            if h == last_h:
                stable += 1
            else:
                stable = 0
            last_h = h
            if stable >= 2:
                break

    async def scroll_to_bottom_cycles(
        self,
        max_cycles: int = 6,
        stable_required: int = 2,
        per_cycle_wheel: int = 3,
        wait_ms: int = 300,
        hide_only: bool = True,
    ) -> List[int]:
        """
        Scroll to bottom with bounded cycles. Each cycle: dismiss (hide only if hide_only), wheel per_cycle_wheel times, wait.
        Stop when scrollHeight unchanged for stable_required consecutive cycles (or after max_cycles).
        Returns list of scrollHeight values per cycle for logging.
        """
        page = self.page
        heights: List[int] = []
        last_h = 0
        stable = 0
        for cycle in range(max_cycles):
            await self.dismiss_overlays(max_rounds=1, aggressive=True, click_close_buttons=not hide_only)
            for _ in range(per_cycle_wheel):
                try:
                    await page.mouse.wheel(0, 2000)
                except Exception:
                    pass
                await page.wait_for_timeout(wait_ms)
            try:
                h = int(await page.evaluate("document.body.scrollHeight"))
            except Exception:
                h = last_h
            heights.append(h)
            if h <= last_h + 2:
                stable += 1
                if stable >= stable_required:
                    break
            else:
                stable = 0
            last_h = h
        return heights

    async def restore_auditor_hidden(self) -> int:
        """Restore elements hidden by dismiss_overlays (data-qa-hidden-by-auditor). Returns count restored."""
        try:
            n = await self.page.evaluate("""
                () => {
                  const els = Array.from(document.querySelectorAll("[data-qa-hidden-by-auditor='1']"));
                  for (const el of els) {
                    el.style.visibility = el.dataset.qaPrevVisibility || "";
                    delete el.dataset.qaHiddenByAuditor;
                    delete el.dataset.qaPrevVisibility;
                  }
                  return els.length;
                }
            """)
            return int(n) if n is not None else 0
        except Exception:
            return 0

    async def dismiss_overlays(
        self,
        max_rounds: int = 4,
        aggressive: bool = True,
        click_close_buttons: bool = True,
    ) -> Dict[str, Any]:
        """
        Dismiss popups/overlays: Escape; then (if click_close_buttons) only safe close buttons;
        then (if aggressive) JS-hide fixed/sticky high-z overlapping viewport center.
        Never clicks "danger" buttons (Allow, Get, Subscribe, OK, Accept all, etc.).
        Returns stats: clicked, hiddenCount, rounds, clickedCloseCount, blockedDangerClicksCount.
        """
        page = self.page
        url = (page.url or "").lower()
        stats: Dict[str, Any] = {
            "clicked": [],
            "hiddenCount": 0,
            "rounds": 0,
            "clickedCloseCount": 0,
            "blockedDangerClicksCount": 0,
        }
        # Safe close: only these selectors; we will skip any element whose text matches DANGER_TEXTS
        DANGER_TEXTS = [
            "allow", "允许", "press to get", "get", "subscribe", "sign in", "register",
            "continue", "ok", "accept all", "同意", "接受", "accept", "confirm", "yes",
        ]
        # AliExpress: only pure close controls first (no generic dialog button)
        safe_close_selectors = [
            ".next-dialog-close",
            "button[aria-label='Close']",
            "button[aria-label='close']",
            "button[aria-label='Stäng']",
            "button[aria-label='stäng']",
            "button:has-text('×')",
            "button:has-text('No thanks')",
            "button:has-text(\"Don't allow\")",
            "button:has-text('Not now')",
            "[data-testid='close']",
            ".close",
            ".close-btn",
            ".modal-close",
            ".dialog-close",
            "button[class*='close']",
        ]
        if "aliexpress" not in url:
            safe_close_selectors.extend([
                "[role='dialog'] button[aria-label*='close' i]",
                "[aria-modal='true'] button[aria-label*='close' i]",
            ])
        for r in range(max_rounds):
            stats["rounds"] = r + 1
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
            if click_close_buttons:
                for sel in safe_close_selectors:
                    try:
                        loc = page.locator(sel)
                        cnt = await loc.count()
                        for i in range(min(cnt, 8)):
                            try:
                                el = loc.nth(i)
                                if not await el.is_visible(timeout=400):
                                    continue
                                # Only button or role=button; never click <a> (navigation); skip if text is danger
                                is_safe = await el.evaluate("""
                                    (el) => {
                                        const tag = (el.tagName || '').toUpperCase();
                                        if (tag === 'A') return false;
                                        const role = (el.getAttribute('role') || '').toLowerCase();
                                        if (tag !== 'BUTTON' && role !== 'button') return false;
                                        const text = ((el.innerText || '') + ' ' + (el.getAttribute('aria-label') || '')).toLowerCase();
                                        const danger = ['allow','允许','press to get','get','subscribe','sign in','register','continue','ok','accept all','同意','接受','accept','confirm','yes'];
                                        for (const d of danger) { if (text.includes(d)) return false; }
                                        const safe = ['close','×','✕','deny','reject','don\'t allow','not now','no thanks','stäng','avvisa','dismiss','cancel'];
                                        for (const s of safe) { if (text.includes(s)) return true; }
                                        return text.trim().length <= 3 || text.includes('x');
                                    }
                                """)
                                if not is_safe:
                                    stats["blockedDangerClicksCount"] = stats.get("blockedDangerClicksCount", 0) + 1
                                    continue
                                await el.click(timeout=800)
                                stats["clickedCloseCount"] = stats.get("clickedCloseCount", 0) + 1
                                if sel not in stats["clicked"]:
                                    stats["clicked"].append(sel)
                                await page.wait_for_timeout(200)
                            except Exception:
                                pass
                    except Exception:
                        pass
            if aggressive:
                try:
                    hidden = await page.evaluate("""
                        () => {
                          const vw = window.innerWidth, vh = window.innerHeight;
                          const cx = vw / 2, cy = vh / 2;
                          const hidden = [];
                          const els = Array.from(document.querySelectorAll("body *"));
                          for (const el of els) {
                            const st = window.getComputedStyle(el);
                            if (st.position !== "fixed" && st.position !== "sticky") continue;
                            const zi = parseInt(st.zIndex || "0", 10);
                            if (!Number.isFinite(zi) || zi < 100) continue;
                            const r = el.getBoundingClientRect();
                            if (r.width * r.height < vw * vh * 0.02) continue;
                            const intersectsCenter = r.left <= cx && r.right >= cx && r.top <= cy && r.bottom >= cy;
                            if (!intersectsCenter) continue;
                            if (el.dataset.qaHiddenByAuditor === "1") continue;
                            el.dataset.qaHiddenByAuditor = "1";
                            el.dataset.qaPrevVisibility = el.style.visibility || "";
                            el.style.setProperty("visibility", "hidden", "important");
                            hidden.push({ tag: el.tagName, zi });
                          }
                          return { hiddenCount: hidden.length, hidden };
                        }
                    """)
                    stats["hiddenCount"] = stats.get("hiddenCount", 0) + (hidden.get("hiddenCount") or 0)
                except Exception:
                    pass
            await page.wait_for_timeout(300)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=2000)
            except Exception:
                pass
        return stats

    async def stabilize_bottom(
        self,
        max_cycles: int = 6,
        settle_ms: int = 900,
        stable_required: int = 2,
    ) -> None:
        """
        Scroll to bottom repeatedly until scrollHeight is stable (for lazy-loaded footer).
        Stops when scrollHeight is unchanged for stable_required consecutive checks, or after max_cycles.
        """
        stable = 0
        last_h: Optional[int] = None
        for _ in range(max_cycles):
            try:
                await self.page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            except Exception:
                pass
            await self.page.wait_for_timeout(settle_ms)
            try:
                h2 = int(await self.page.evaluate("() => document.body.scrollHeight"))
            except Exception:
                h2 = last_h or 0
            if last_h is not None and h2 == last_h:
                stable += 1
                if stable >= stable_required:
                    return
            else:
                stable = 0
            last_h = h2

    async def _hide_common_overlays_css(self) -> None:
        """Inject CSS to hide modal/dialog/backdrop, chat/support widgets, and floating toolbars (e.g. AliExpress)."""
        css = """
        /* modal/dialog/backdrop */
        [role="dialog"], [aria-modal="true"], .modal, .Modal, .dialog, .Dialog,
        .backdrop, .Backdrop, .overlay, .Overlay,
        [class*="backdrop"], [class*="overlay"], [class*="modal"] {
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        /* chat/support floating widgets */
        [id*="chat"], [class*="chat"], [class*="Chat"],
        [id*="support"], [class*="support"], [class*="Support"],
        [class*="help"], [class*="Help"],
        [class*="intercom"], [id*="intercom"],
        [class*="zendesk"], [id*="zendesk"],
        [class*="freshchat"], [id*="freshchat"],
        [class*="crisp"], [id*="crisp"],
        [class*="launcher"], [id*="launcher"] {
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        /* AliExpress / right floating toolbar */
        [class*="right-side"], [class*="RightSide"], [class*="side-bar"], [class*="SideBar"],
        [class*="float"], [class*="Float"], [class*="fixed-tool"], [class*="FixedTool"] {
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        """
        try:
            await self.page.add_style_tag(content=css)
        except Exception:
            pass

    async def ensure_no_overlays(self, retry: int = 1) -> None:
        """
        Inject CSS to hide common overlays (modal/backdrop/chat). No click, minimal wait.
        AliExpress etc.: clicking overlays can trigger refresh or re-popup; we only need visual hide for evidence.
        """
        for _ in range(retry):
            try:
                await self._hide_common_overlays_css()
            except Exception:
                pass
            await self.page.wait_for_timeout(150)

    async def scroll_to_true_bottom(
        self,
        max_ms: int = 10_000,
        step_px: int = 1400,
        settle_ms: int = 180,
        stable_rounds: int = 2,
    ) -> None:
        """
        Scroll to true bottom using wheel (not scrollTo) to trigger lazy-loaded footer.
        Stops when scrollHeight is unchanged for stable_rounds and viewport is near bottom.
        Use before overlay clear so footer/Klarna icons have a chance to render.
        """
        import time
        start = time.monotonic()
        stable = 0
        last_h = -1
        while (time.monotonic() - start) * 1000 < max_ms:
            try:
                h = await self.page.evaluate("() => document.documentElement.scrollHeight")
            except Exception:
                h = last_h
            try:
                await self.page.mouse.wheel(0, step_px)
            except Exception:
                pass
            await self.page.wait_for_timeout(settle_ms)
            try:
                h2 = await self.page.evaluate("() => document.documentElement.scrollHeight")
                near_bottom = await self.page.evaluate(
                    "() => { const el = document.documentElement; return el.scrollTop + window.innerHeight >= el.scrollHeight - 4; }"
                )
            except Exception:
                h2 = h
                near_bottom = False
            if h2 == last_h and near_bottom:
                stable += 1
                if stable >= stable_rounds:
                    break
            else:
                stable = 0
            last_h = h2
        try:
            await self.page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
        except Exception:
            pass
        await self.page.wait_for_timeout(200)

    async def ensure_no_overlays_fast(self, max_passes: int = 2) -> None:
        """
        Clear overlays after at bottom: ESC, safe close buttons (close/dismiss/Not now/No thanks),
        then CSS-hide large fixed/sticky overlays (cover ≥18%, height ≥90px).
        Prefers CSS hide over aggressive clicking to avoid triggering page refresh (e.g. on AliExpress).
        Use after scroll_to_true_bottom.
        """
        for pass_num in range(max_passes):
            try:
                await self.page.keyboard.press("Escape")
            except Exception:
                pass
            await self.page.wait_for_timeout(120)
            close_selectors = [
                "button[aria-label*='close' i]", "button[aria-label*='dismiss' i]", "button[aria-label*='cancel' i]",
                "[role='dialog'] button:has-text('×')", "[role='dialog'] button:has-text('Close')",
                "[role='dialog'] button:has-text('No')", "[role='dialog'] button:has-text(\"Don't allow\")",
                "[role='dialog'] button:has-text('Not now')", "button:has-text('No thanks')",
                "div[role='dialog'] .close", "div[role='dialog'] .closeBtn", "div[class*='modal' i] button[class*='close' i]",
                "div[class*='popup' i] button[class*='close' i]", "[class*='close' i][role='button']",
            ]
            for sel in close_selectors:
                try:
                    loc = self.page.locator(sel).first
                    if await loc.count() > 0 and await loc.is_visible(timeout=300):
                        await loc.click(timeout=800)
                        await self.page.wait_for_timeout(120)
                except Exception:
                    pass
            await self.page.evaluate("""
                () => {
                    const vw = window.innerWidth, vh = window.innerHeight;
                    const candidates = Array.from(document.querySelectorAll("body *")).filter(el => {
                        const style = window.getComputedStyle(el);
                        if (style.visibility === "hidden" || style.display === "none") return false;
                        if (style.position !== "fixed" && style.position !== "sticky") return false;
                        const r = el.getBoundingClientRect();
                        if ((r.width * r.height) / (vw * vh) < 0.18) return false;
                        if (r.height < 90) return false;
                        const tag = el.tagName.toLowerCase();
                        if (tag === "html" || tag === "body") return false;
                        return true;
                    });
                    candidates.forEach(el => {
                        el.setAttribute("data-e2e-hidden-overlay", "1");
                        el.style.setProperty("visibility", "hidden", "important");
                        el.style.setProperty("pointer-events", "none", "important");
                    });
                }
            """)
            await self.page.wait_for_timeout(150)
            try:
                has_dialog = await self.page.locator("[role='dialog'], [aria-modal='true'], .modal, .popup, .overlay").first.is_visible()
            except Exception:
                has_dialog = False
            if not has_dialog:
                break

    async def bring_footer_into_view_stable(self) -> None:
        """After at bottom: scroll to bottom, then wheel up a bit and down so footer payment area is stable in viewport."""
        try:
            await self.page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
        except Exception:
            pass
        await self.page.wait_for_timeout(200)
        try:
            await self.page.mouse.wheel(0, -260)
        except Exception:
            pass
        await self.page.wait_for_timeout(220)
        try:
            await self.page.mouse.wheel(0, 360)
        except Exception:
            pass
        await self.page.wait_for_timeout(220)

    async def freeze_scroll(self) -> None:
        """Freeze page scroll (html/body overflow hidden) so screenshot is not affected by infinite-load during capture."""
        await self.page.evaluate("""
        () => {
          if (window.__klarna_auditor_freeze__) return;
          window.__klarna_auditor_freeze__ = true;
          const style = document.createElement('style');
          style.id = '__klarna_auditor_freeze_style__';
          style.textContent = `
            html, body { overflow: hidden !important; }
          `;
          document.head.appendChild(style);
        }
        """)

    async def unfreeze_scroll(self) -> None:
        """Remove scroll freeze (restore html/body overflow). Call after screenshot/match phase."""
        await self.page.evaluate("""
        () => {
          const style = document.getElementById('__klarna_auditor_freeze_style__');
          if (style) style.remove();
          window.__klarna_auditor_freeze__ = false;
        }
        """)

    async def hide_overlays_overlapping_bbox(self, x: float, y: float, w: float, h: float) -> int:
        """Hide only fixed/sticky elements that overlap the given bbox (document coords). Returns hidden count."""
        try:
            n = await self.page.evaluate(
                """(params) => {
                  const target = { left: params.x, top: params.y, right: params.x + params.w, bottom: params.y + params.h };
                  const hidden = [];
                  const els = Array.from(document.querySelectorAll("body *"));
                  for (const el of els) {
                    const st = getComputedStyle(el);
                    if (st.position !== "fixed" && st.position !== "sticky") continue;
                    const zi = parseInt(st.zIndex || "0", 10);
                    if (!Number.isFinite(zi) || zi < 10) continue;
                    const r = el.getBoundingClientRect();
                    const elLeft = r.left + window.scrollX, elTop = r.top + window.scrollY;
                    const elRight = elLeft + r.width, elBottom = elTop + r.height;
                    const overlap = !(elRight < target.left || elLeft > target.right || elBottom < target.top || elTop > target.bottom);
                    if (!overlap) continue;
                    if (el.dataset.qaHiddenByAuditor === "1") continue;
                    el.dataset.qaHiddenByAuditor = "1";
                    el.dataset.qaPrevVisibility = el.style.visibility || "";
                    el.style.setProperty("visibility", "hidden", "important");
                    hidden.push(1);
                  }
                  return hidden.length;
                }""",
                {"x": x, "y": y, "w": w, "h": h},
            )
            return int(n) if n is not None else 0
        except Exception:
            return 0

    async def clear_overlays(self, reason: str = "") -> None:
        """Clear popups/overlays: soft close (ESC + click close buttons) then hard hide (inject CSS)."""
        page = self.page
        print(f"[DEBUG] clear_overlays start ({reason})")

        for i in range(3):
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
            close_locators = [
                "button[aria-label='Close']",
                "button[aria-label='close']",
                "button[aria-label='Stäng']",
                "button[aria-label='stäng']",
                "[role='dialog'] button[aria-label*='close' i]",
                "[aria-modal='true'] button[aria-label*='close' i]",
                "button:has-text('Tillåt alla')",
                "button:has-text('Acceptera')",
                "button:has-text('Avvisa')",
                "button:has-text('Reject')",
                "button:has-text('Accept')",
                "button:has-text('OK')",
            ]
            for sel in close_locators:
                try:
                    loc = page.locator(sel).first
                    if await loc.count() > 0 and await loc.is_visible(timeout=400):
                        await loc.click(timeout=800)
                        await page.wait_for_timeout(250)
                except Exception:
                    continue
            try:
                for char in ["×", "✕"]:
                    loc = page.get_by_text(char, exact=True)
                    if await loc.count() > 0:
                        el = loc.first
                        if await el.is_visible(timeout=400):
                            await el.click(timeout=800)
                            await page.wait_for_timeout(250)
                            break
            except Exception:
                pass
            await page.wait_for_timeout(300)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=2000)
            except Exception:
                pass

        css = """
        [role="dialog"], [aria-modal="true"], .modal, .Modal, .popup, .Popup,
        .overlay, .Overlay, .backdrop, .BackDrop,
        .cookie, .Cookie, .consent, .Consent,
        [id*="cookie" i], [class*="cookie" i],
        [id*="consent" i], [class*="consent" i],
        [id*="gdpr" i], [class*="gdpr" i],
        [id*="popup" i], [class*="popup" i],
        [id*="modal" i], [class*="modal" i],
        [id*="overlay" i], [class*="overlay" i],
        iframe[id*="popup" i], iframe[class*="popup" i],
        iframe[id*="modal" i], iframe[class*="modal" i]
        { display: none !important; visibility: hidden !important; }
        [class*="chat" i], [id*="chat" i],
        [class*="support" i], [id*="support" i],
        [class*="intercom" i], [id*="intercom" i],
        [class*="messenger" i], [id*="messenger" i]
        { display: none !important; visibility: hidden !important; }
        * { scroll-behavior: auto !important; }
        """
        try:
            await page.add_style_tag(content=css)
        except Exception:
            pass
        try:
            await page.evaluate("""
            () => {
              const nodes = Array.from(document.querySelectorAll('body *'));
              for (const el of nodes) {
                const s = window.getComputedStyle(el);
                if (!s) continue;
                const z = parseInt(s.zIndex || '0', 10);
                if ((s.position === 'fixed' || s.position === 'sticky') && z >= 999) {
                  el.style.setProperty('display', 'none', 'important');
                  el.style.setProperty('visibility', 'hidden', 'important');
                }
              }
            }
            """)
        except Exception:
            pass
        await page.wait_for_timeout(300)
        print(f"[DEBUG] clear_overlays done ({reason})")

    async def scroll_to_bottom(self) -> None:
        print("[DEBUG] Scrolling to bottom before footer check")
        for _ in range(5):
            try:
                await self.page.evaluate("window.scrollBy(0, document.body.scrollHeight / 4)")
            except Exception:
                break
            await self.page.wait_for_timeout(300)
        try:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        except Exception:
            pass
        await self.page.wait_for_timeout(800)

    async def _looks_like_pdp(self, timeout_ms: int = 3000) -> bool:
        """Check if current page looks like a product detail page (price, add-to-cart, product-id, etc.)."""
        pdp_selectors = [
            "[data-product-id]",
            "[class*='product-price']",
            "[class*='product_price']",
            "[data-price]",
            "button:has-text('Add to cart')",
            "button:has-text('Læg i kurv')",
            "button:has-text('Tilføj til kurv')",
            "button:has-text('Køb')",
            "[data-add-to-cart]",
            "[class*='add-to-cart']",
        ]
        for sel in pdp_selectors:
            try:
                loc = self.page.locator(sel).first
                if await loc.count() > 0 and await loc.is_visible(timeout=timeout_ms):
                    return True
            except Exception:
                continue
        try:
            body = await self.page.locator("body").text_content()
            if body and ("add to cart" in body.lower() or "læg i kurv" in body.lower() or "pris" in body.lower() or "price" in body.lower()):
                return True
        except Exception:
            pass
        return False
    
    async def auto_pick_pdp(self) -> Optional[str]:
        """Pick a PDP URL from home. jula.se: use /erbjudanden/ + catalog links; others: URL pattern + tile fallback."""
        parsed = urlparse(self.home_url or "")
        host = (parsed.netloc or "").lower()

        # ==== jula.se: list page + catalog links ending with 5–7 digits ====
        if host.endswith("jula.se"):
            print("[DEBUG] auto_pick_pdp: host=jula.se, using /erbjudanden/ strategy")
            try:
                await self.page.goto(self.home_url, wait_until="domcontentloaded", timeout=10000)
                await self.dismiss_cookie_banner()
            except Exception:
                pass
            jula_list_url = f"{parsed.scheme or 'https'}://{parsed.netloc}/erbjudanden/"
            try:
                await self.page.goto(jula_list_url, wait_until="domcontentloaded", timeout=10000)
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                await self.dismiss_cookie_banner()
            except Exception as e:
                print(f"[DEBUG] jula.se: goto erbjudanden failed: {e}")
                return None
            try:
                links = await self.page.eval_on_selector_all(
                    "a[href*='/catalog/']",
                    "els => els.map(e => e.href)"
                )
            except Exception as e:
                print(f"[DEBUG] jula.se: eval catalog links failed: {e}")
                return None
            if not isinstance(links, list):
                links = []
            print(f"[DEBUG] jula.se: found {len(links)} catalog-like links")
            pdp_candidates = [href for href in links if isinstance(href, str) and re.search(r"/\d{5,7}/?$", href)]
            if pdp_candidates:
                pdp_url = pdp_candidates[0]
            elif links:
                pdp_url = links[0]
                print("[DEBUG] jula.se: no PDP candidate with 5–7 digit suffix, using first /catalog/ link")
            else:
                print("[DEBUG] jula.se: no catalog links found")
                return None
            print(f"[DEBUG] jula.se: auto-picked PDP URL = {pdp_url}")
            try:
                await self.page.goto(pdp_url, wait_until="domcontentloaded", timeout=10000)
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                await self.dismiss_cookie_banner()
            except Exception:
                return None
            return self.page.url

        # ==== Shein: go to RecommendSelection listing (e.g. .../RecommendSelection/Women-Tops), then pick a product ====
        if "shein" in host:
            base = (parsed.scheme or "https") + "://" + (parsed.netloc or "")
            home_norm = (self.home_url or "").rstrip("/").lower()
            # Fixed listing URL: same host, path RecommendSelection/Women-Tops-sc-017175498.html
            shein_listing_url = base.rstrip("/") + "/RecommendSelection/Women-Tops-sc-017175498.html"
            print(f"[DEBUG] auto_pick_pdp: host=shein, using listing {shein_listing_url}")
            await try_close_common_overlays(self.page)
            await hide_high_zindex_overlays(self.page)
            await self.page.wait_for_timeout(400)
            try:
                await self.page.goto(shein_listing_url, wait_until="domcontentloaded", timeout=12000)
                await self.page.wait_for_timeout(1500)
            except Exception as e:
                print(f"[DEBUG] auto_pick_pdp: shein goto listing failed: {e}")
                return self.home_url

            # Shein has no -p-/-g- product URLs on listing; clicking any image in the center goes to PDP
            await self.page.wait_for_timeout(800)
            # Scroll so product grid is in view
            try:
                await self.page.evaluate("window.scrollBy(0, 300)")
                await self.page.wait_for_timeout(400)
            except Exception:
                pass
            # Click an image in the center of the viewport (product image -> PDP)
            clicked = await self.page.evaluate(
                """() => {
                  const vw = window.innerWidth, vh = window.innerHeight;
                  const centerMinX = vw * 0.2, centerMaxX = vw * 0.8;
                  const centerMinY = vh * 0.2, centerMaxY = vh * 0.8;
                  const imgs = document.querySelectorAll('main img, [class*="product"] img, [class*="goods"] img, [class*="slick"] img, img[loading="lazy"]');
                  for (const img of imgs) {
                    const r = img.getBoundingClientRect();
                    if (r.width < 80 || r.height < 80) continue;
                    const cx = r.left + r.width/2, cy = r.top + r.height/2;
                    if (cx >= centerMinX && cx <= centerMaxX && cy >= centerMinY && cy <= centerMaxY) {
                      const clickable = img.closest('a') || img;
                      clickable.click();
                      return true;
                    }
                  }
                  return false;
                }"""
            )
            if clicked:
                await self.page.wait_for_load_state("domcontentloaded")
                await self.page.wait_for_timeout(1500)
                if await self._looks_like_pdp():
                    print(f"[DEBUG] auto_pick_pdp: Shein PDP confirmed at {self.page.url}")
                    return self.page.url
            print("[DEBUG] auto_pick_pdp: Shein strategy did not find PDP")
            return self.home_url

        # ==== Other sites: strict URL patterns first (exclude /p/order, /p/cart), then tile click fallback ====
        await try_close_common_overlays(self.page)
        await hide_high_zindex_overlays(self.page)
        await self.page.wait_for_timeout(300)
        for _ in range(3):
            try:
                await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
            except Exception:
                break
            await self.page.wait_for_timeout(300)

        base = (parsed.scheme or "https") + "://" + (parsed.netloc or "")

        async def try_goto_and_confirm(url: str) -> bool:
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=10000)
                await self.page.wait_for_timeout(800)
                return await self._looks_like_pdp()
            except Exception:
                return False

        # 1) Strict product-link strategy: good_path_patterns, exclude bad_path_patterns
        try:
            anchors = await self.page.query_selector_all("a[href]")
            for a in anchors:
                href = await a.get_attribute("href")
                if not href or href.startswith("javascript:"):
                    continue
                lower = href.lower()
                if any(b in lower for b in BAD_PATH_PATTERNS):
                    continue
                if any(g in lower for g in GOOD_PATH_PATTERNS):
                    candidate = urljoin(base + "/", href)
                    if candidate == (self.home_url or "").rstrip("/") or (candidate.endswith("/") and candidate.rstrip("/") == (self.home_url or "").rstrip("/")):
                        continue
                    print(f"[DEBUG] auto_pick_pdp: trying good-path candidate {candidate}")
                    if await try_goto_and_confirm(candidate):
                        print(f"[DEBUG] auto_pick_pdp: PDP confirmed at {self.page.url}")
                        return self.page.url
                    break  # one good-path try; if failed, fall through to step 2
        except Exception:
            pass
        # If step 1 navigated away but didn't confirm PDP, return to home for step 2
        try:
            home_norm = (self.home_url or "").rstrip("/")
            if home_norm and self.page.url.rstrip("/") != home_norm:
                await self.page.goto(self.home_url or "", wait_until="domcontentloaded", timeout=10000)
                await self.page.wait_for_timeout(500)
        except Exception:
            pass

        # 2) Candidate href selectors (existing behavior)
        for sel in CANDIDATE_HREF_SELECTORS:
            try:
                anchors = await self.page.query_selector_all(sel)
                for a in anchors:
                    href = await a.get_attribute("href")
                    if not href:
                        continue
                    if any(x in href.lower() for x in EXCLUDE_PATTERNS):
                        continue
                    candidate = urljoin(base + "/", href)
                    if candidate == (self.home_url or "").rstrip("/") or candidate == (self.home_url or "").rstrip("/") + "/":
                        continue
                    print(f"[DEBUG] auto_pick_pdp: trying candidate {candidate}")
                    if await try_goto_and_confirm(candidate):
                        print(f"[DEBUG] auto_pick_pdp: PDP confirmed at {self.page.url}")
                        return self.page.url
            except Exception:
                continue

        # 3) Fallback: click first visible product tile / product-card link
        for sel in TILE_SELECTORS:
            try:
                node = await self.page.query_selector(sel)
                if node and await node.is_visible():
                    await node.scroll_into_view_if_needed()
                    await node.click()
                    await self.page.wait_for_load_state("domcontentloaded")
                    await self.page.wait_for_timeout(800)
                    if await self._looks_like_pdp():
                        print(f"[DEBUG] auto_pick_pdp: PDP via tile at {self.page.url}")
                        return self.page.url
            except Exception:
                continue

        # 4) Final fallback: first internal anchor (href starts with /)
        try:
            anchors = await self.page.query_selector_all("a[href]")
            for a in anchors:
                href = await a.get_attribute("href")
                if href and href.startswith("/") and len(href) > 3:
                    if any(b in href.lower() for b in BAD_PATH_PATTERNS):
                        continue
                    candidate = urljoin(base + "/", href)
                    print(f"[DEBUG] auto_pick_pdp: trying internal fallback {candidate}")
                    if await try_goto_and_confirm(candidate):
                        print(f"[DEBUG] auto_pick_pdp: PDP via internal at {self.page.url}")
                        return self.page.url
                    break
        except Exception:
            pass

        print("[DEBUG] auto_pick_pdp: no PDP found, returning home")
        return self.home_url
    
    async def navigate_to_home(self, home_url: str) -> bool:
        """Navigate to HOME page"""
        try:
            await self.page.goto(home_url, wait_until='domcontentloaded', timeout=10000)
            try:
                await self.page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                pass
            await self.dismiss_cookie_banner()
            await try_close_common_overlays(self.page)
            await hide_known_overlays(self.page)
            await dismiss_overlays(self.page, debug=True)
            return True
        except Exception:
            return False
    
    async def navigate_to_pdp(self, pdp_url: Optional[str]) -> Optional[str]:
        """Navigate to PDP. If no pdp_url or same as home, auto_pick_pdp. Returns actual URL or None."""
        if not pdp_url or (self.home_url and pdp_url.strip("/") == self.home_url.strip("/")):
            await self.navigate_to_home(self.home_url or pdp_url or "")
            pdp_url = await self.auto_pick_pdp()
            if not pdp_url:
                print("[DEBUG] navigate_to_pdp: auto PDP failed, staying on HOME_URL")
                pdp_url = self.home_url
        else:
            try:
                await self.page.goto(pdp_url, wait_until='domcontentloaded', timeout=10000)
                try:
                    await self.page.wait_for_load_state('networkidle', timeout=10000)
                except Exception:
                    pass
                await self.dismiss_cookie_banner()
                await hide_known_overlays(self.page)
                await dismiss_overlays(self.page, debug=True)
            except Exception:
                return None
        await dismiss_overlays(self.page, debug=True)
        print(f"[DEBUG] navigate_to_pdp: final url = {self.page.url}")
        return self.page.url
    
    async def handle_required_options(self) -> Dict[str, Any]:
        """
        Handle all required options before adding to cart:
        - Select elements: choose first valid option if value is empty
        - Radio buttons: click first enabled if group not selected
        - Button variants: click first enabled button/option in area with "Vælg" text
        
        Returns: dict with debug info about what was selected
        """
        debug_info = {
            'selects_handled': [],
            'radios_handled': [],
            'buttons_handled': [],
            'vælg_detected': False
        }
        
        try:
            # Check if page contains "Vælg" text (using locator)
            try:
                body_text = await self.page.locator("body").text_content()
                if body_text and 'vælg' in body_text.lower():
                    debug_info['vælg_detected'] = True
                    print("[DEBUG] Detected 'Vælg' text on page")
            except Exception:
                pass
            
            # 1. Handle select elements
            try:
                selects = await self.page.query_selector_all('select')
                for select in selects:
                    try:
                        current_value = await select.input_value()
                        is_disabled = await select.get_attribute('disabled')
                        
                        current_value = await select.input_value()
                        placeholder = await select.get_attribute('placeholder')
                        if not is_disabled and (not current_value or current_value == '' or placeholder):
                            # Get first enabled option
                            options = await select.query_selector_all('option:not([disabled]):not([value=""])')
                            if options:
                                first_option = options[0]
                                option_value = await first_option.get_attribute('value')
                                option_text = await first_option.inner_text()
                                
                                await select.select_option(value=option_value)
                                await self.page.wait_for_timeout(500)
                                
                                debug_info['selects_handled'].append({
                                    'value': option_value,
                                    'text': option_text.strip()
                                })
                                print(f"[DEBUG] Selected option: {option_text.strip()} (value: {option_value})")
                    except Exception:
                        continue
            except Exception:
                pass
            
            # 2. Handle radio buttons
            try:
                # Group radios by name
                radio_groups = {}
                radios = await self.page.query_selector_all('input[type="radio"]:not([disabled])')
                
                for radio in radios:
                    try:
                        name = await radio.get_attribute('name')
                        if name:
                            if name not in radio_groups:
                                radio_groups[name] = []
                            radio_groups[name].append(radio)
                    except Exception:
                        continue
                
                # For each group, check if any is selected
                for name, group_radios in radio_groups.items():
                    try:
                        # Check if any radio in group is checked
                        any_checked = False
                        for radio in group_radios:
                            if await radio.is_checked():
                                any_checked = True
                                break
                        
                        # If none checked, click first enabled
                        if not any_checked and group_radios:
                            first_radio = group_radios[0]
                            await first_radio.scroll_into_view_if_needed()
                            await self.page.wait_for_timeout(300)
                            await first_radio.click()
                            wait_time = 600  # 300-800ms range
                            await self.page.wait_for_timeout(wait_time)
                            
                            value = await first_radio.get_attribute('value')
                            debug_info['radios_handled'].append({
                                'name': name,
                                'value': value
                            })
                            print(f"[DEBUG] Selected radio: {name} = {value}")
                    except Exception:
                        continue
            except Exception:
                pass
            
            # 3. Handle button variants (fallback if /Vælg/i found)
            if debug_info['vælg_detected']:
                try:
                    # Find first enabled button/option near "Vælg" text
                    variant_buttons = await self.page.query_selector_all(
                        '*:has-text("Vælg") button:not([disabled]), '
                        '*:has-text("Vælg") [class*="option"]:not([disabled]), '
                        '*:has-text("Vælg") [role="button"]:not([disabled])'
                    )
                    if variant_buttons:
                        first_button = variant_buttons[0]
                        if await first_button.is_visible():
                            await first_button.scroll_into_view_if_needed()
                            await first_button.click()
                            await self.page.wait_for_timeout(600)
                            button_text = await first_button.inner_text()
                            debug_info['buttons_handled'].append({'text': button_text.strip() if button_text else ''})
                            print(f"[DEBUG] Clicked variant button: {button_text.strip() if button_text else 'N/A'}")
                except Exception:
                    pass
            
            return debug_info
        except Exception as e:
            print(f"[DEBUG] Error in handle_required_options: {str(e)}")
            return debug_info
    
    async def add_to_cart(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Click add to cart button on PDP with required options handling
        
        Returns: (success, debug_info)
        """
        debug_info = {
            'options_handled': {},
            'button_clicked': None,
            'button_text': None,
            'mini_cart_detected': False,
            'url_changed_to_cart': False,
            'final_url': None
        }
        
        # Wait for page to be ready
        try:
            await self.page.wait_for_load_state('networkidle', timeout=10000)
        except Exception:
            pass
        
        # Handle cookie consent
        await handle_cookie_consent(self.page)
        await asyncio.sleep(0.5)
        
        # Handle required options first
        options_info = await self.handle_required_options()
        debug_info['options_handled'] = options_info
        
        # Find product scope
        scope = await find_product_scope(self.page)
        
        # Dump CTAs in scope
        ctas, elems = await dump_ctas_in_scope(self.page, scope, max_items=80)
        
        # Filter candidates
        candidates = []
        for idx, txt in ctas:
            if ATC_EXCLUDE.search(txt):
                continue
            if ATC_INCLUDE.search(txt):
                candidates.append((idx, txt))
        
        if not candidates:
            # Save debug HTML if no candidates
            try:
                html = await scope.inner_html()
                os.makedirs("out", exist_ok=True)
                timestamp = int(asyncio.get_event_loop().time())
                fname = f"out/jula_debug_scope_{timestamp}.html"
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"[DEBUG] Saved scope HTML to {fname}")
            except Exception:
                pass
            print("[DEBUG] ATC failed - Button: None (no candidate)")
            debug_info['final_url'] = self.page.url
            return False, debug_info
        
        # Prefer exact "lägg i (kundvagn|varukorg)"
        pref = re.compile(r"lägg\s+i\s*(kundvagn|varukorg)", re.I)
        chosen = None
        for idx, txt in candidates:
            if pref.search(txt):
                chosen = (idx, txt)
                break
        if not chosen:
            chosen = candidates[0]
        idx, chosen_text = chosen
        
        # Click ATC
        try:
            loc = scope.locator(f":text-matches('{re.escape(chosen_text)}','i')").first
            if await loc.count() and await loc.is_visible():
                await click_by_js(loc)
                print(f"[DEBUG] Clicked ATC: '{chosen_text}'")
            else:
                raise Exception("Locator not found")
        except Exception:
            try:
                target_elem = elems.nth(idx)
                await click_by_js(target_elem)
                print(f"[DEBUG] Fallback clicked ATC by index: '{chosen_text}'")
            except Exception:
                print("[DEBUG] Failed to click chosen ATC")
                debug_info['final_url'] = self.page.url
                return False, debug_info
        
        debug_info['button_text'] = chosen_text
        await self.page.wait_for_timeout(500)
        
        # If "Vælg" / "Choose" selection panel appeared, fill selects/radios and click modal CTA
        vælg_visible = False
        try:
            for text in ["Vælg", "vælg", "Choose"]:
                loc = self.page.get_by_text(text, exact=False).first
                if await loc.count() > 0 and await loc.is_visible(timeout=300):
                    vælg_visible = True
                    print(f"[DEBUG] Selection panel detected: '{text}'")
                    break
        except Exception:
            pass
        
        if vælg_visible:
            # Select first non-empty option in each select
            try:
                selects = await self.page.query_selector_all("select")
                for sel in selects:
                    try:
                        if await sel.is_disabled():
                            continue
                        opts = await sel.query_selector_all("option")
                        n = len(opts) if opts else 0
                        if n == 0:
                            continue
                        # Prefer index 1 (first non-empty option; 0 often placeholder)
                        for idx in [1, 0]:
                            if idx < n:
                                try:
                                    await sel.select_option(index=idx)
                                    await self.page.wait_for_timeout(200)
                                    break
                                except Exception:
                                    continue
                    except Exception:
                        continue
            except Exception as e:
                print(f"[DEBUG] Selects handling: {e}")
            # Check first enabled radio per group (click first enabled)
            try:
                radios = await self.page.query_selector_all('input[type="radio"]')
                for r in radios:
                    try:
                        if await r.is_enabled():
                            await r.click()
                            await self.page.wait_for_timeout(300)
                            break
                    except Exception:
                        continue
            except Exception:
                pass
            # Click modal primary CTA
            candidate_btns = [
                'button:has-text("Tilføj til kurv")',
                'button:has-text("Tilføj til vogn")',
                'button:has-text("Fortsæt")',
                'button:has-text("Fortsæt")',
                'button:has-text("Gå til kurv")',
                '.modal button.primary',
                '[role="dialog"] button:has-text("Tilføj")',
                '[role="dialog"] button:has-text("Fortsæt")',
            ]
            for sel in candidate_btns:
                try:
                    btn = self.page.locator(sel).first
                    if await btn.count() > 0 and await btn.is_visible(timeout=400):
                        await click_by_js(btn)
                        print(f"[DEBUG] Clicked modal CTA: {sel}")
                        await self.page.wait_for_timeout(700)
                        if await self._detect_atc_success():
                            debug_info["selection_panel_cta_clicked"] = sel
                            break
                except Exception:
                    continue
            # If still not success, try confirmation modal (Bekræft / Confirm)
            if not await self._detect_atc_success():
                for confirm_text in ["Bekræft", "Confirm"]:
                    try:
                        confirm_btn = self.page.get_by_role("button", name=re.compile(re.escape(confirm_text), re.I)).first
                        if await confirm_btn.count() > 0 and await confirm_btn.is_visible(timeout=400):
                            await click_by_js(confirm_btn)
                            print(f"[DEBUG] Clicked confirmation: {confirm_text}")
                            await self.page.wait_for_timeout(500)
                            break
                    except Exception:
                        continue
        
        # Handle post-ATC modals
        success = await handle_post_atc_modals_helper(self.page)
        
        # Check URL for cart
        if re.search(r"/cart|/varukorg|/kundvagn", self.page.url, re.I):
            success = True
        if not success and await self._detect_atc_success():
            success = True
        
        if success:
            print("[DEBUG] ATC flow succeeded (entered cart)")
        else:
            print("[DEBUG] ATC flow possibly failed; no cart detected yet")
        
        debug_info['final_url'] = self.page.url
        return success, debug_info
    
    async def handle_post_atc_modals(self) -> Tuple[bool, Dict[str, Any]]:
        """Handle multi-step upsell modals after ATC click"""
        debug_info = {'modal_steps': [], 'final_url': None}
        
        for step in range(3):
            try:
                # Find visible dialog
                dialog = None
                try:
                    dialog = self.page.get_by_role("dialog").first
                    if not await dialog.is_visible(timeout=1000):
                        dialog = None
                except Exception:
                    pass
                
                if not dialog:
                    try:
                        dialog_loc = self.page.locator("[role='dialog']:visible, .modal:visible, .c-modal:visible").first
                        if await dialog_loc.is_visible(timeout=1000):
                            dialog = dialog_loc
                    except Exception:
                        pass
                
                if not dialog:
                    break
                
                # Find buttons in dialog
                buttons = await dialog.locator("button, a, [role='button']").all()
                
                for btn in buttons:
                    try:
                        btn_text = await btn.inner_text()
                        if not btn_text:
                            continue
                        
                        btn_text_lower = btn_text.strip().lower()
                        is_enabled = await btn.is_enabled()
                        
                        # Priority 1: "Gå till kundvagn/varukorg" / "Go to cart" (Swedish)
                        if re.search(r'gå\s*(till|til|i)\s*(kundvagn|varukorg)|go\s*to\s*cart', btn_text_lower) and is_enabled:
                            print(f"[DEBUG] Modal step {step+1}: Clicked '{btn_text.strip()}'")
                            await btn.click()
                            # Wait for /cart|varukorg|kundvagn in URL (10s)
                            for _ in range(10):
                                await self.page.wait_for_timeout(1000)
                                url_lower = self.page.url.lower()
                                if any(x in url_lower for x in ['/cart', '/varukorg', '/kundvagn']):
                                    debug_info['modal_steps'].append(f"step_{step+1}_cart_clicked")
                                    debug_info['final_url'] = self.page.url
                                    return True, debug_info
                            debug_info['modal_steps'].append(f"step_{step+1}_cart_clicked_no_url")
                            continue
                        
                        # Priority 2: "Nej tack" / "No thanks" / "Skip" / "Avbryt"
                        elif re.search(r'nej\s*tack|no\s*thanks|skip|avbryt', btn_text_lower) and is_enabled:
                            print(f"[DEBUG] Modal step {step+1}: Clicked '{btn_text.strip()}'")
                            await btn.click()
                            await self.page.wait_for_timeout(500)  # 300-800ms
                            debug_info['modal_steps'].append(f"step_{step+1}_skip")
                            break
                        
                        # Priority 3: "Fortsätt" / "Continue" / "Nästa" (Swedish)
                        elif re.search(r'forts[aä]tt|fortsaet|continue|nästa|nästa steg', btn_text_lower) and is_enabled:
                            print(f"[DEBUG] Modal step {step+1}: Clicked '{btn_text.strip()}'")
                            await btn.click()
                            await self.page.wait_for_timeout(500)  # 300-800ms
                            debug_info['modal_steps'].append(f"step_{step+1}_continue")
                            break
                    except Exception:
                        continue
            except Exception as e:
                print(f"[DEBUG] Modal step {step+1} error: {str(e)}")
                break
        
        # Fallback: click header cart icon (Swedish patterns)
        try:
            cart_icon = self.page.locator("a[href*='/cart'], a[href*='varukorg'], a[href*='kundvagn'], button[aria-label*='cart']").first
            if await cart_icon.is_visible(timeout=2000):
                print("[DEBUG] Fallback: Clicking cart icon in header")
                await cart_icon.click()
                await self.page.wait_for_timeout(2000)
                for _ in range(8):
                    await self.page.wait_for_timeout(1000)
                    url_lower = self.page.url.lower()
                    if any(x in url_lower for x in ['/cart', '/varukorg', '/kundvagn']):
                        debug_info['modal_steps'].append("fallback_cart_icon")
                        debug_info['final_url'] = self.page.url
                        return True, debug_info
        except Exception:
            pass
        
        debug_info['final_url'] = self.page.url
        return False, debug_info
    
    async def _detect_atc_success(self) -> bool:
        """
        Check if add-to-cart succeeded:
        - URL is cart/varukorg/kundvagn, or
        - .cart-count visible and > 0 / checkout button visible, or
        - "added to cart" toast text, or
        - Sidebar/drawer cart open and contains items
        """
        try:
            url_lower = self.page.url.lower()
            if any(x in url_lower for x in ['/cart', '/varukorg', '/kundvagn']):
                print("[DEBUG] _detect_atc_success: URL is cart")
                return True
        except Exception:
            pass
        try:
            cart_count = self.page.locator(".cart-count, [class*='cart-count'], [data-cart-count]").first
            if await cart_count.count() > 0 and await cart_count.is_visible(timeout=500):
                text = await cart_count.text_content()
                if text and text.strip().isdigit() and int(text.strip()) > 0:
                    print("[DEBUG] _detect_atc_success: cart count > 0")
                    return True
        except Exception:
            pass
        try:
            checkout_btn = self.page.locator("button:has-text('Checkout'), a:has-text('Checkout'), button:has-text('Kassen'), a:has-text('Kassen'), [class*='checkout']").first
            if await checkout_btn.count() > 0 and await checkout_btn.is_visible(timeout=300):
                print("[DEBUG] _detect_atc_success: checkout button visible")
                return True
        except Exception:
            pass
        try:
            body = await self.page.locator("body").text_content()
            if body:
                lower = body.lower()
                if any(phrase in lower for phrase in [
                    "added to cart", "tilføjet til kurv", "lagt i kurv", "læg i kurv",
                    "läggts till", "lagts till i varukorgen", "er blevet tilføjet"
                ]):
                    print("[DEBUG] _detect_atc_success: success toast/text")
                    return True
        except Exception:
            pass
        try:
            drawer = self.page.locator("[class*='mini-cart']:visible, [class*='cart-drawer']:visible, [class*='side-drawer']:visible, [id*='mini-cart']:visible").first
            if await drawer.count() > 0 and await drawer.is_visible(timeout=300):
                items = await drawer.locator("[class*='cart-item'], [class*='line-item'], [data-product], .product-row").count()
                if items > 0:
                    print("[DEBUG] _detect_atc_success: sidebar cart with items")
                    return True
        except Exception:
            pass
        return False

    async def verify_add_to_cart_success(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify add to cart success by checking:
        a) URL changed to /cart
        b) Visible modal/dialog contains "er blevet tilføjet til kurven" OR button "Fortsæt" OR "Gå til kurv"
        
        Returns: (success, debug_info)
        """
        debug_info = {
            'url_changed_to_cart': False,
            'modal_detected': False,
            'final_url': None
        }
        
        # Wait up to 10s for success signals
        for _ in range(10):
            await self.page.wait_for_timeout(1000)
            
            # Check if URL changed to cart (Swedish: varukorg/kundvagn)
            current_url = self.page.url
            debug_info['final_url'] = current_url
            url_lower = current_url.lower()
            if any(x in url_lower for x in ['/cart', '/varukorg', '/kundvagn']):
                debug_info['url_changed_to_cart'] = True
                print("[DEBUG] Success signal: URL changed to cart")
                return True, debug_info
            
            # Check for modal with success text (Swedish: läggts till i varukorgen/kundvagn)
            try:
                dialog = self.page.locator(".modal, [role='dialog']").first
                if await dialog.is_visible(timeout=500):
                    dialog_text = await dialog.text_content()
                    if dialog_text and re.search(r'läggts till i (varukorgen|kundvagn)|tilføjet til kurven|er blevet tilføjet til kurven', dialog_text, re.I):
                        debug_info['modal_detected'] = True
                        print("[DEBUG] Success signal: Modal contains 'added to cart' text")
                        return True, debug_info
                    
                    # Check for "Fortsätt" / "Gå till kundvagn" buttons in modal (Swedish)
                    try:
                        fortsätt_btn = dialog.locator(":text-matches('forts[aä]tt|fortsaet', 'i')").first
                        if await fortsätt_btn.is_visible(timeout=500):
                            debug_info['modal_detected'] = True
                            print("[DEBUG] Success signal: Modal contains 'Fortsätt' button")
                            return True, debug_info
                    except Exception:
                        pass
                    
                    try:
                        kurv_btn = dialog.locator(":text-matches('gå\\s*(till|til|i)\\s*(kundvagn|varukorg)', 'i')").first
                        if await kurv_btn.is_visible(timeout=500):
                            debug_info['modal_detected'] = True
                            print("[DEBUG] Success signal: Modal contains 'Gå till kundvagn' button")
                            return True, debug_info
                    except Exception:
                        pass
            except Exception:
                pass
        
        return False, debug_info
        
        # Check for "Gå til kurv" / "Til kurv" button (mini-cart)
        cart_button_selectors = [
            'button:has-text("Gå til kurv")',
            'button:has-text("Til kurv")',
            'a:has-text("Gå til kurv")',
            'a:has-text("Til kurv")',
            '[href*="/cart"]:has-text("kurv")'
        ]
        
        for selector in cart_button_selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=1500, state='visible')  # Reduced
                if element:
                    debug_info['mini_cart_detected'] = True
                    print("[DEBUG] Mini-cart button detected, clicking...")
                    
                    # Click to go to cart
                    await element.scroll_into_view_if_needed()
                    await element.click()
                    await self.page.wait_for_timeout(1000)  # Reduced from 1500
                    
                    # Verify we're now on cart page
                    new_url = self.page.url
                    debug_info['final_url'] = new_url
                    if '/cart' in new_url.lower():
                        debug_info['mini_cart_clicked'] = True
                        debug_info['url_changed_to_cart'] = True
                        print("[DEBUG] Clicked mini-cart, navigated to /cart - SUCCESS")
                        return True, debug_info
                    else:
                        print(f"[DEBUG] Mini-cart clicked but URL is: {new_url}")
            except Exception:
                continue
        
        # Check for mini-cart or side drawer
        mini_cart_selectors = [
            '[class*="mini-cart"]',
            '[class*="side-drawer"]',
            '[class*="cart-drawer"]',
            '[id*="mini-cart"]',
            '[id*="cart-drawer"]'
        ]
        
        for selector in mini_cart_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    debug_info['mini_cart_detected'] = True
                    print("[DEBUG] Mini-cart drawer detected")
                    
                    # Try to find and click "View cart" or similar
                    view_cart_buttons = await element.query_selector_all('button:has-text("kurv"), a[href*="/cart"]')
                    if view_cart_buttons:
                        await view_cart_buttons[0].scroll_into_view_if_needed()
                        await view_cart_buttons[0].click()
                        await self.page.wait_for_timeout(1000)  # Reduced
                        
                        new_url = self.page.url
                        if '/cart' in new_url.lower():
                            debug_info['mini_cart_clicked'] = True
                            debug_info['url_changed_to_cart'] = True
                            print("[DEBUG] Clicked view cart in drawer, navigated to /cart - SUCCESS")
                            return True, debug_info
            except Exception:
                continue
        
        print("[DEBUG] No success signal detected")
        return False, debug_info
    
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
            except Exception:
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
