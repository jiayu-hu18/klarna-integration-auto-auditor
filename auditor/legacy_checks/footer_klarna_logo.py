"""
Check 1: FOOTER_KLARNA_LOGO

Verifies Klarna logo in the footer "Pay with" / payment methods area.

Flow:
1. Scroll to true bottom (wheel) to trigger lazy-loaded footer; then clear overlays and bring footer into view.
2. Locate "Pay with" / "Payment methods" / "We accept" etc. via text match; take element screenshot of that container only (no full viewport/ROI crop to avoid false positives like "Choice" in product grid).
3. Multi-template image matching on the payments section screenshot; template-specific aspect-ratio filter (wordmark ≥1.8, pink badge ≥1.15) to reject narrow matches.
4. PASS only when match is in the payments section and passes ratio; evidence = footer_payments_section_attempt*.png (must visibly show Klarna).
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
from playwright.async_api import Page, ElementHandle, Locator
from auditor.navigator import Navigator
from auditor.screenshot import ScreenshotManager
from auditor.report import CheckResult, Evidence
from auditor.utils import find_element_in_frames, get_element_snippet_and_path, find_klarna_text_in_footer
from auditor import vision


@dataclass
class KlarnaMatch:
    """Result of template matching in footer ROI."""
    found: bool
    best_score: float
    bbox: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h) relative to ROI image
    roi_path: Optional[str] = None
    roi_expanded_path: Optional[str] = None
    match_debug_path: Optional[str] = None
    best_template_path: Optional[str] = None
    all_templates: Optional[List[Dict[str, Any]]] = None

# Multi-template: discover from assets or use explicit list (legacy_checks -> auditor/assets)
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
def _load_template_paths() -> List[str]:
    discovered = vision.discover_templates(ASSETS_DIR)
    if discovered:
        return discovered
    fallback = [
        str(ASSETS_DIR / "klarna_payment_back.png"),
        str(ASSETS_DIR / "klarna_wordmark_black.png"),
        str(ASSETS_DIR / "klarna_wordmark_pink.png"),
    ]
    return [p for p in fallback if Path(p).is_file()]

MATCH_THRESHOLD = 0.75  # template match score threshold
# Lower threshold for white-on-dark / clear templates (e.g. Kickscrew footer)
FOOTER_CLEAR_WHITEBG_THRESHOLD = 0.63
FOOTER_MAX_RETRIES = 2


def _threshold_for_template(template_path: str) -> float:
    """Use lower threshold for white_bg / footer_clear / clear_black templates (white-on-dark logos)."""
    name = Path(template_path).name.lower()
    if "white_bg" in name or "footer_clear" in name or "clear_black" in name:
        return FOOTER_CLEAR_WHITEBG_THRESHOLD
    return MATCH_THRESHOLD  # scroll-to-bottom → overlay clear → bring footer into view → screenshot payments section; retry once if no pass

# ROI selector candidates for footer payment area (try first before full footer)
FOOTER_PAYMENT_ROI_SELECTORS = [
    ".payments", ".payment-icons", ".footer-payments", ".footer__payments", ".site-footer .payments",
]

# Overlay selectors to hide (visibility:hidden + pointer-events:none) before footer capture
OVERLAY_SELECTORS = [
    '[role="dialog"]',
    '.chat-widget, .livechat, .intercom-widget, .support-float, .help-chat',
    '.cookie-modal, .cookie-consent, #cookie-banner, .gdpr-popup',
    '.subscribe-modal, .newsletter-modal',
    '.sticky-footer, .floating-footer, .fixed-cta',
]


async def _hide_overlays(page: Page) -> None:
    """Hide common overlays so footer is visible. Records hidden nodes for optional restore."""
    await page.evaluate(
        """(selectors) => {
        window.__hidden_overlays = [];
        selectors.forEach(s => {
          try {
            document.querySelectorAll(s).forEach(el => {
              if (el && el.style) {
                window.__hidden_overlays.push({sel: s, node: el});
                el.setAttribute('data-hidden-by-auditor', '1');
                el.style.visibility = 'hidden';
                el.style.pointerEvents = 'none';
              }
            });
          } catch(e){}
        });
      }""",
        OVERLAY_SELECTORS,
    )


async def _restore_overlays(page: Page) -> None:
    """Restore overlays hidden by _hide_overlays (optional, e.g. after debug screenshot)."""
    await page.evaluate(
        """() => {
        document.querySelectorAll('[data-hidden-by-auditor="1"]').forEach(el => {
          el.style.visibility = '';
          el.style.pointerEvents = '';
          el.removeAttribute('data-hidden-by-auditor');
        });
      }"""
    )


async def _try_template_match_on_footer(
    page: Page,
    screenshot_manager: ScreenshotManager,
    template_paths: List[str],
    screenshot_path: str,
    expand_roi: bool = False,
) -> Dict[str, Any]:
    """
    Find payment section by text (Pay with / Payment methods / We accept / etc.), screenshot that container, run multi-template match.
    When pay_label is not found, returns found=False without running template match on full page (avoids false positive on "Choice").
    Returns dict: found, best_match, best_score, best_bbox, all_templates, roi_path, match_input_path, screenshot_path.
    """
    result = {
        "found": False,
        "best_match": None,
        "best_score": 0.0,
        "best_bbox": None,
        "all_templates": [],
        "roi_path": None,
        "match_input_path": None,
        "screenshot_path": screenshot_path,
    }
    pay_label = page.locator(
        ":text-matches('pay\\\\s*with|payment\\\\s*methods|we\\\\s*accept|pay\\\\s*after\\\\s*delivery|klarna|du kan betala med|betala med|betal|payment', 'i')"
    ).first
    if await pay_label.count() == 0:
        # NO global matching – avoid false positives on product grid (e.g. "Choice")
        result["match_input_path"] = None
        return result
    # expand_roi: use ancestor [2] (wider) else [1]
    ancestor_index = "2" if expand_roi else "1"
    roi = pay_label.locator(f"xpath=ancestor::*[name()='div' or name()='section'][{ancestor_index}]")
    if await roi.count() == 0:
        roi = pay_label.locator("xpath=ancestor::*[name()='div' or name()='section'][1]")
    roi_path = None
    if await roi.count() > 0:
        try:
            roi_path = screenshot_manager._generate_path("footer_payments_roi" + ("_expanded" if expand_roi else ""))
            await roi.first.screenshot(path=roi_path)
        except Exception:
            roi_path = None
    match_input = roi_path or screenshot_path
    result["roi_path"] = roi_path
    result["match_input_path"] = match_input
    for tp in template_paths:
        th = _threshold_for_template(tp)
        mr = vision.match_template_in_image(match_input, tp, threshold=th, try_inverted=True)
        rec = {"template_path": tp, "score": mr.get("score", 0.0), "bbox": mr.get("bbox"), "found": mr.get("found", False)}
        result["all_templates"].append(rec)
        if (rec["score"] or 0) > (result["best_score"] or 0):
            result["best_score"] = rec["score"]
            result["best_bbox"] = rec["bbox"]
            result["best_match"] = {**mr, "needle_path": tp}
            result["found"] = rec["found"]
    return result


# Attributes to scan for "klarna" in payment section (fallback)
KLARNA_ATTRS = ["src", "srcset", "href", "data-src", "data-srcset", "alt", "title", "aria-label", "style"]
MAX_ELEMENTS_SCAN = 500


def _min_ratio_for_template(tp: str) -> float:
    """Minimum bbox aspect ratio (w/h) per template. Wordmark is wider; pink badge is squarer. Rejects narrow false positives (e.g. 'Choice')."""
    name = Path(tp).name.lower()
    if "wordmark_black" in name or ("wordmark" in name and "pink" not in name):
        return 1.8
    if "pink" in name:
        return 1.15
    # white_bg / clear_black often used for icon-shaped white-on-dark logos; allow squarer bbox
    if "white_bg" in name or "footer_clear" in name or "clear_black" in name:
        return 0.8
    return 1.3


def _bbox_aspect_ratio(bbox: Any) -> Optional[float]:
    """Return bbox aspect ratio w/h, or None if invalid. bbox = (x, y, w, h). Used with _min_ratio_for_template to filter matches."""
    if not bbox or len(bbox) != 4:
        return None
    w, h = bbox[2], bbox[3]
    if h <= 0:
        return None
    return w / h


def _match_klarna_on_roi_image(
    roi_path: str,
    debug_dir: Path,
    attempt: int,
    template_paths: List[str],
) -> KlarnaMatch:
    """
    Run multi-template match on an existing ROI image (e.g. footer element screenshot).
    Only candidates that pass score threshold AND template-specific aspect ratio (w/h >= min_ratio) count as best.
    """
    if not Path(roi_path).is_file():
        return KlarnaMatch(False, 0.0, None, None, None, None, None, [])

    best: Optional[Dict[str, Any]] = None
    all_templates: List[Dict[str, Any]] = []

    for tp in template_paths:
        th = _threshold_for_template(tp)
        mr = vision.match_template_in_image(roi_path, tp, threshold=th, try_inverted=True)
        score = mr.get("score", 0.0) or 0.0
        bbox = mr.get("bbox")
        rec = {"template_path": tp, "score": score, "bbox": bbox, "found": mr.get("found", False)}
        all_templates.append(rec)

        if score < th or not bbox:
            continue
        ratio = _bbox_aspect_ratio(bbox)
        min_ratio = _min_ratio_for_template(tp)
        if ratio is None or ratio < min_ratio:
            continue
        if best is None or score > best["score"]:
            best = {"tp": tp, "score": score, "bbox": bbox, "mr": mr}

    found = best is not None
    best_score = best["score"] if best else 0.0
    best_bbox = best["bbox"] if best else None
    best_template_path = best["tp"] if best else None
    match_debug_path = None
    if found and best_bbox:
        match_debug_path = str(debug_dir / f"footer_roi_match_debug_attempt{attempt}_score{best_score:.3f}.png")
        vision.draw_match_overlay(roi_path, match_debug_path, list(best_bbox), color=(0, 255, 0), thickness=4)

    return KlarnaMatch(
        found=found,
        best_score=best_score or 0.0,
        bbox=tuple(best_bbox) if best_bbox and len(best_bbox) == 4 else None,
        roi_path=roi_path,
        roi_expanded_path=None,
        match_debug_path=match_debug_path,
        best_template_path=best_template_path,
        all_templates=all_templates,
    )


async def detect_klarna_in_footer_with_templates(
    page: Page,
    footer_locator: Locator,
    debug_dir: Path,
    attempt: int,
    template_paths: List[str],
) -> KlarnaMatch:
    """
    Take footer element screenshot only (no full page), then run template match on it.
    Caller must have called freeze_scroll() before this so scroll does not trigger lazy load.
    Evidence: footer_evidence_attempt{n}.png and footer_payments_roi_attempt{n}.png (same image).
    """
    import shutil
    footer_evidence_path = str(debug_dir / f"footer_evidence_attempt{attempt}.png")
    roi_path = str(debug_dir / f"footer_payments_roi_attempt{attempt}.png")

    try:
        await footer_locator.first.screenshot(path=footer_evidence_path)
    except Exception:
        return KlarnaMatch(False, 0.0, None, None, None, None, None, [])

    if not Path(footer_evidence_path).is_file():
        return KlarnaMatch(False, 0.0, None, None, None, None, None, [])

    try:
        shutil.copy(footer_evidence_path, roi_path)
    except Exception:
        roi_path = footer_evidence_path

    return _match_klarna_on_roi_image(roi_path, debug_dir, attempt, template_paths)


PAGE_BOTTOM_MAX_HEIGHT = 800


async def screenshot_page_bottom(page: Page, output_path: str, max_height: int = PAGE_BOTTOM_MAX_HEIGHT) -> Optional[str]:
    """
    Scroll to bottom, wait for footer to render, then take viewport screenshot (what's
    visible at the bottom). Crop to bottom max_height (800px) if viewport is taller.
    Saves to output_path. Returns output_path if success else None.
    """
    import tempfile
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.5)
    except Exception:
        pass
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        await page.screenshot(path=tmp_path)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        return None
    if not Path(tmp_path).is_file():
        return None
    img_w, img_h = vision.get_image_size(tmp_path)
    if img_h <= 0 or img_w <= 0:
        Path(tmp_path).unlink(missing_ok=True)
        return None
    roi_h = min(max_height, img_h)
    roi_y = img_h - roi_h
    out = vision.crop_roi_from_image(tmp_path, 0, roi_y, img_w, roi_h, output_path)
    Path(tmp_path).unlink(missing_ok=True)
    return out if out and Path(output_path).is_file() else None


async def screenshot_payments_section(page: Page, debug_dir: Path, attempt: int) -> Optional[str]:
    """
    Locate footer payment area by text (Pay with / Payment methods / We accept / pay after delivery / klarna),
    find nearest div/section container, take element screenshot. Returns path or None if not found.
    When None, no template match is run (avoids false positive on product grid e.g. "Choice").
    """
    pay_label = page.locator(
        ":text-matches('pay\\\\s*with|payment\\\\s*methods|we\\\\s*accept|pay\\\\s*after\\\\s*delivery|klarna', 'i')"
    ).first
    if await pay_label.count() == 0:
        return None
    container = pay_label.locator("xpath=ancestor::*[name()='div' or name()='section'][1]")
    if await container.count() == 0:
        return None
    path = str(debug_dir / f"footer_payments_section_attempt{attempt}.png")
    try:
        await container.first.screenshot(path=path)
    except Exception:
        return None
    return path if Path(path).is_file() else None


async def detect_klarna_in_footer_roi_viewport(
    page: Page,
    debug_dir: Path,
    attempt: int,
    template_paths: List[str],
) -> KlarnaMatch:
    """
    Take viewport screenshot (evidence), crop bottom 50% as ROI, run template match on ROI.
    DEPRECATED for main flow: use screenshot_payments_section + _match_klarna_on_roi_image instead.
    """
    evidence_path = str(debug_dir / f"footer_evidence_attempt{attempt}.png")
    roi_path = str(debug_dir / f"footer_payments_roi_attempt{attempt}.png")
    try:
        await page.screenshot(path=evidence_path)
    except Exception:
        return KlarnaMatch(False, 0.0, None, None, None, None, None, [])

    if not Path(evidence_path).is_file():
        return KlarnaMatch(False, 0.0, None, None, None, None, None, [])

    img_w, img_h = vision.get_image_size(evidence_path)
    if img_h <= 0 or img_w <= 0:
        return KlarnaMatch(False, 0.0, None, evidence_path, None, None, None, [])

    roi_h = max(400, int(img_h * 0.5))
    roi_y = img_h - roi_h
    vision.crop_roi_from_image(evidence_path, 0, roi_y, img_w, roi_h, roi_path)
    if not Path(roi_path).is_file():
        roi_path = evidence_path

    return _match_klarna_on_roi_image(roi_path, debug_dir, attempt, template_paths)


async def detect_klarna_in_footer(footer: Locator) -> Tuple[bool, Dict[str, Any]]:
    """
    Detect Klarna in footer via visible text or img/svg alt|aria-label|title.
    Fallback: locate payment section ("Du kan betala med"), then scan element attributes (and img/svg outerHTML) for "klarna".
    Returns (found, evidence) with evidence containing matched_selector and/or matched_text.
    """
    # 1) Text search
    try:
        text_locator = footer.locator(":text-matches('Klarna', 'i')")
        if await text_locator.count() > 0:
            first_text = text_locator.first
            if await first_text.is_visible():
                text = (await first_text.inner_text() or "").strip()
                print(f"[DEBUG] Footer Klarna detected via text: '{text[:80]}'")
                return True, {
                    "matched_selector": ":text-matches('Klarna','i')",
                    "matched_text": text[:200] if text else "Klarna",
                }
    except Exception:
        pass

    # 2) alt / aria-label / title
    try:
        attr_locator = footer.locator(
            "img[alt*='Klarna' i], img[alt*='klarna' i], "
            "svg[aria-label*='Klarna' i], [aria-label*='Klarna' i], [aria-label*='klarna' i], "
            "[title*='Klarna' i], [title*='klarna' i]"
        )
        if await attr_locator.count() > 0:
            first_el = attr_locator.first
            if await first_el.is_visible():
                alt = await first_el.get_attribute("alt")
                aria = await first_el.get_attribute("aria-label")
                title = await first_el.get_attribute("title")
                text = alt or aria or title or "Klarna logo"
                if isinstance(text, str):
                    text = text.strip()
                print(f"[DEBUG] Footer Klarna detected via alt/aria-label/title: '{text}'")
                return True, {
                    "matched_selector": "img/svg[alt|aria-label|title*='Klarna']",
                    "matched_text": text[:200] if isinstance(text, str) else str(text),
                }
    except Exception:
        pass

    # 3) Fallback: payment section ("Du kan betala med") -> scan scope elements for klarna in attrs / img|svg outerHTML
    try:
        pay_section = footer.locator(":text-matches('Du kan betala med', 'i')").first
        scope = pay_section if await pay_section.count() > 0 else footer
        # Helper: check one element's attrs and (if img/svg) outerHTML for "klarna"
        async def _el_has_klarna(el: Locator, tag_hint: str) -> Tuple[bool, Dict[str, Any]]:
            tag = tag_hint
            if not tag:
                try:
                    tag = (await el.evaluate("e => e.tagName ? e.tagName.toLowerCase() : ''")) or "element"
                except Exception:
                    tag = "element"
            for attr in KLARNA_ATTRS:
                try:
                    val = await el.get_attribute(attr)
                    if val and "klarna" in val.lower():
                        return True, {"matched_selector": tag, "matched_text": f"{attr}={val[:200]}"}
                except Exception:
                    continue
            if tag in ("img", "svg"):
                try:
                    outer = await el.evaluate("e => e.outerHTML || ''")
                    if outer and "klarna" in outer.lower():
                        return True, {"matched_selector": tag, "matched_text": "outerHTML contains klarna"}
                except Exception:
                    pass
            return False, {}

        # Check scope element itself first
        scope_tag = ""
        try:
            scope_tag = (await scope.evaluate("e => e.tagName ? e.tagName.toLowerCase() : ''")) or ""
        except Exception:
            pass
        found_scope, ev_scope = await _el_has_klarna(scope, scope_tag)
        if found_scope:
            print(f"[DEBUG] Footer Klarna detected via attr in payment scope: {ev_scope.get('matched_text', '')[:80]}")
            return True, ev_scope

        all_els = scope.locator("*")
        n = min(MAX_ELEMENTS_SCAN, await all_els.count())
        for i in range(n):
            el = all_els.nth(i)
            found_el, ev_el = await _el_has_klarna(el, "")
            if found_el:
                print(f"[DEBUG] Footer Klarna detected via attr in payment scope: {ev_el.get('matched_text', '')[:80]}")
                return True, ev_el
    except Exception:
        pass

    return False, {}


async def detect_klarna_in_bottom_of_page(page: Page) -> Tuple[bool, Optional[ElementHandle], Dict[str, Any]]:
    """
    Fallback: search whole page for visible 'Klarna' and check if it lies in the bottom
    half of the document (footer area). Returns (found, element_handle, evidence).
    """
    try:
        doc_height = await page.evaluate("() => document.body.scrollHeight") or 0
        if doc_height <= 0:
            return False, None, {}
        threshold = doc_height * 0.5  # bottom half = footer area
        locator = page.locator(":text-matches('Klarna', 'i')")
        count = await locator.count()
        for i in range(count):
            el = locator.nth(i)
            if not await el.is_visible():
                continue
            box = await el.bounding_box()
            if box and box.get("y", 0) >= threshold:
                text = (await el.inner_text() or "").strip().replace("\n", " ")[:200]
                handle = await el.element_handle()
                print(f"[DEBUG] Footer fallback: Klarna in bottom of page: '{text[:80]}'")
                return True, handle, {
                    "matched_selector": "page_bottom_klarna",
                    "matched_text": text or "Klarna",
                }
        # Also check img/svg in bottom half
        attr_loc = page.locator(
            "img[alt*='Klarna' i], img[alt*='klarna' i], "
            "[aria-label*='Klarna' i], [aria-label*='klarna' i], [title*='Klarna' i], [title*='klarna' i]"
        )
        for i in range(await attr_loc.count()):
            el = attr_loc.nth(i)
            if not await el.is_visible():
                continue
            box = await el.bounding_box()
            if box and box.get("y", 0) >= threshold:
                handle = await el.element_handle()
                alt = await el.get_attribute("alt") or await el.get_attribute("aria-label") or await el.get_attribute("title") or "Klarna"
                print(f"[DEBUG] Footer fallback: Klarna (alt/aria) in bottom of page")
                return True, handle, {"matched_selector": "page_bottom_klarna", "matched_text": str(alt)[:200]}
    except Exception:
        pass
    return False, None, {}


class FooterKlarnaLogoCheck:
    """
    Check 1: FOOTER_KLARNA_LOGO.
    Uses freeze + evidence-first: scroll to bottom, clear overlays, bring footer into view,
    then freeze scroll and screenshot only the payments section; template match with aspect-ratio filter.
    """
    
    CHECK_ID = "FOOTER_KLARNA_LOGO"
    
    async def execute(
        self,
        page: Page,
        navigator: Navigator,
        screenshot_manager: ScreenshotManager,
        home_url: str
    ) -> CheckResult:
        """
        Execute footer Klarna logo check.
        Flow: scroll_to_true_bottom → ensure_no_overlays_fast → bring_footer_into_view_stable →
        for each attempt: freeze_scroll → screenshot_payments_section (Pay with container) →
        _match_klarna_on_roi_image (template + aspect-ratio filter). PASS only when evidence is payments section with Klarna.
        """
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

            # 2. Load templates (assert non-empty)
            template_paths = _load_template_paths()
            if not template_paths:
                try:
                    files = list(ASSETS_DIR.glob("*.png")) if ASSETS_DIR.is_dir() else []
                    print(f"[{self.CHECK_ID}] Template dir: {ASSETS_DIR} files: {[f.name for f in files]}")
                except Exception as e:
                    print(f"[{self.CHECK_ID}] Template dir list error: {e}")
                raise RuntimeError("No templates loaded for footer Klarna match")
            print(f"[{self.CHECK_ID}] templates_count={len(template_paths)}")

            debug_dir = Path(screenshot_manager.merchant_dir) / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)

            # 3. Wait for page ready
            await navigator.wait_for_page_ready(
                selectors=['footer', '[class*="footer"]', '[id*="footer"]'],
                timeout=10000
            )

            found = False
            best_score = 0.0
            best_bbox = None
            best_template_path = None
            all_templates: List[Dict[str, Any]] = []
            screenshot_path = ""
            roi_path = None
            match_debug_path = None
            page_bottom_screenshot_path: Optional[str] = None

            # Step A: Scroll to true bottom (wheel) to trigger lazy-loaded footer / Klarna icons
            await navigator.scroll_to_true_bottom(
                max_ms=9_000, settle_ms=160, stable_rounds=2, step_px=1600
            )

            # Step B: Clear overlays (ESC + safe close buttons + CSS-hide large fixed/sticky)
            await navigator.ensure_no_overlays_fast(max_passes=2)

            # Step C: Bring footer payment area stably into viewport
            await navigator.bring_footer_into_view_stable()

            # Brief wait so lazy-loaded footer content (e.g. AliExpress) has time to paint
            await asyncio.sleep(1.5)

            # Screenshot whole bottom of page (max height 800px), regardless of pass/fail
            page_bottom_screenshot_path = await screenshot_page_bottom(
                page, str(debug_dir / "footer_page_bottom.png"), max_height=PAGE_BOTTOM_MAX_HEIGHT
            )

            for attempt in range(1, FOOTER_MAX_RETRIES + 1):
                print(f"[{self.CHECK_ID}] attempt={attempt}")
                await navigator.freeze_scroll()
                try:
                    roi_path_attempt = await screenshot_payments_section(page, debug_dir, attempt)

                    if not roi_path_attempt:
                        # Payments section not found: save viewport for debug only; no template match (avoids false positive on product grid)
                        try:
                            await page.screenshot(path=str(debug_dir / f"footer_evidence_attempt{attempt}.png"))
                        except Exception:
                            pass
                        match = KlarnaMatch(False, 0.0, None, None, None, None, None, [])
                    else:
                        match = _match_klarna_on_roi_image(roi_path_attempt, debug_dir, attempt, template_paths)

                    if match.found:
                        print(f"[{self.CHECK_ID}] PASS at attempt {attempt} score={match.best_score:.4f}; evidence: {roi_path_attempt} match_debug={match.match_debug_path}")
                        evidence = Evidence(
                            screenshot_path=roi_path_attempt,
                            roi_screenshot_path=roi_path_attempt,
                            best_template_path=match.best_template_path,
                            best_score=round(match.best_score, 4),
                            best_bbox=list(match.bbox) if match.bbox else None,
                            all_templates=match.all_templates or [],
                            debug_overlay_path=match.match_debug_path,
                            template_match_score=round(match.best_score, 4),
                            template_bbox=list(match.bbox) if match.bbox else None,
                            template_path=match.best_template_path,
                            matched_text=f"Klarna found in footer payments section (score={match.best_score:.3f})",
                            page_bottom_screenshot_path=page_bottom_screenshot_path,
                        )
                        return CheckResult(
                            check_id=self.CHECK_ID,
                            status="PASS",
                            evidence=evidence,
                            timestamp=datetime.now().isoformat() + "Z",
                            error_reason=None,
                        )

                    if (match.best_score or 0) > best_score:
                        best_score = match.best_score or 0.0
                        best_bbox = match.bbox
                        best_template_path = match.best_template_path
                        all_templates = match.all_templates or []
                        screenshot_path = str(debug_dir / f"footer_evidence_attempt{attempt}.png")
                        roi_path = roi_path_attempt or match.roi_path
                        match_debug_path = match.match_debug_path
                finally:
                    await navigator.unfreeze_scroll()

                # If no PASS: retry once with scroll-to-bottom → overlay clear → bring footer → screenshot → match
                if attempt == 1:
                    await navigator.scroll_to_true_bottom(
                        max_ms=6_000, settle_ms=160, stable_rounds=2, step_px=1600
                    )
                    await navigator.ensure_no_overlays_fast(max_passes=2)
                    await navigator.bring_footer_into_view_stable()

            # Text fallback
            text_fallback = await find_klarna_text_in_footer(page)
            if text_fallback:
                found = True
                print(f"[{self.CHECK_ID}] Klarna text found in footer (text fallback)")

            if not found:
                print(f"[{self.CHECK_ID}] Template match best score: {best_score:.4f} (threshold {MATCH_THRESHOLD})")

            debug_overlay_path = None
            if best_bbox and (roi_path or screenshot_path) and Path(str(roi_path or screenshot_path)).is_file():
                debug_overlay_path = str(debug_dir / "footer_roi_match_debug.png")
                vision.draw_match_overlay(
                    roi_path or screenshot_path,
                    debug_overlay_path,
                    list(best_bbox) if best_bbox else [],
                    color=(0, 255, 255),
                    thickness=3,
                )

            matched_text_evidence = "klarna text found in footer" if text_fallback else None
            evidence = Evidence(
                screenshot_path=screenshot_path or "",
                roi_screenshot_path=roi_path,
                best_template_path=best_template_path,
                best_score=round(best_score, 4) if best_score is not None else None,
                best_bbox=list(best_bbox) if best_bbox else None,
                all_templates=all_templates,
                debug_overlay_path=debug_overlay_path,
                template_match_score=round(best_score, 4) if best_score is not None else None,
                template_bbox=list(best_bbox) if best_bbox else None,
                template_path=best_template_path,
                matched_text=matched_text_evidence,
                page_bottom_screenshot_path=page_bottom_screenshot_path,
            )
            status = "PASS" if found else "FAIL"
            error_reason = None if found else "Klarna logo not found in footer (template match)"
            print(f"[{self.CHECK_ID}] {status}" + (f" best_score={best_score:.4f}" if best_score else ""))
            if error_reason:
                print(f"[{self.CHECK_ID}] Error: {error_reason}")
            await _restore_overlays(page)
            return CheckResult(
                check_id=self.CHECK_ID,
                status=status,
                evidence=evidence,
                timestamp=datetime.now().isoformat() + "Z",
                error_reason=error_reason,
            )

        except Exception as e:
            print(f"[{self.CHECK_ID}] Exception: {str(e)}")
            try:
                await _restore_overlays(page)
            except Exception:
                pass
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
    
    async def detect_klarna_in_footer_legacy(
        self,
        page: Page,
        footer: Optional[ElementHandle]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Legacy: detect Klarna in footer (ElementHandle). Prefer detect_klarna_in_footer(Locator)."""
        if footer:
            try:
                footer_text = await footer.inner_text()
                if footer_text and "klarna" in footer_text.lower():
                    return True, None, "Klarna found in footer text"
            except Exception:
                pass
        return False, None, None
