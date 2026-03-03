"""
CLI entry point: detection-first pipeline; legacy footer/PDP checks only when ENABLE_LEGACY_FOOTER_CHECKS=true.
"""
import argparse
import asyncio
import os
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from auditor.navigator import Navigator
from auditor.screenshot import ScreenshotManager
from auditor.report import ReportGenerator, CheckResult, Evidence
from auditor.detection import collect_page_signals, attach_network_collector, detect
from datetime import datetime

ENABLE_LEGACY_FOOTER_CHECKS = os.environ.get("ENABLE_LEGACY_FOOTER_CHECKS", "false").strip().lower() == "true"

# Domain suffix -> locale when --locale is not provided (check longer suffixes first, e.g. .co.uk before .com)
DOMAIN_LOCALE_MAP = {
    ".co.uk": "en-GB",
    ".com": "en-US",
    ".se": "sv-SE",
    ".dk": "da-DK",
    ".de": "de-DE",
    ".nl": "nl-NL",
    ".fr": "fr-FR",
}


def url_to_merchant_slug(url: str) -> str:
    """e.g. https://www.humac.dk -> humac.dk, https://www.jula.se -> jula.se"""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.netloc or parsed.path or url).lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host or "merchant"


def guess_locale_from_url(base_url: str) -> str:
    url = base_url.lower()
    if ".dk" in url:
        return "da-DK"
    if ".se" in url:
        return "sv-SE"
    if ".no" in url:
        return "nb-NO"
    if ".fi" in url:
        return "fi-FI"
    return "en-US"


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Klarna Integration Auto Auditor - Phase 0 (Single Merchant)'
    )
    parser.add_argument(
        '--out-dir',
        required=True,
        help='Output directory for reports and screenshots'
    )
    parser.add_argument(
        '--headless',
        type=lambda x: x.lower() == 'true',
        default=True,
        help='Run browser in headless mode (default: true)'
    )
    parser.add_argument(
        '--headed',
        action='store_true',
        help='Run browser with visible window (overrides --headless, useful for debugging)'
    )
    parser.add_argument(
        '--slowmo',
        type=int,
        default=0,
        help='Slow down operations by specified milliseconds (for debugging, e.g., 200)'
    )
    parser.add_argument(
        '--locale',
        default=None,
        help='Browser locale (default: guessed from HOME_URL)'
    )
    parser.add_argument(
        '--merchant',
        default='https://www.jula.se',
        help='Merchant URL or domain (default: https://www.jula.se). e.g. https://www.humac.dk'
    )
    parser.add_argument(
        '--only',
        default=None,
        metavar='CHECK_ID',
        help='Run only this check (e.g. FOOTER_KLARNA_LOGO or footer). Omit to run all checks.'
    )
    return parser.parse_args()


async def main():
    """Main execution function"""
    args = parse_args()
    
    # Handle --headed flag (overrides --headless)
    headless_mode = not args.headed if args.headed else args.headless

    home_url = args.merchant if "://" in args.merchant else f"https://www.{args.merchant}"
    merchant_slug = url_to_merchant_slug(home_url)

    if not args.locale:
        parsed = urlparse(home_url)
        for k, v in sorted(DOMAIN_LOCALE_MAP.items(), key=lambda x: -len(x[0])):
            if parsed.netloc and parsed.netloc.lower().endswith(k):
                args.locale = v
                break

    locale = args.locale or guess_locale_from_url(home_url)
    
    print("=" * 60)
    print("Klarna Integration Auto Auditor - Phase 0")
    print("=" * 60)
    print(f"Merchant: {merchant_slug} ({home_url})")
    print(f"Output directory: {args.out_dir}")
    print(f"Headless: {headless_mode}")
    print(f"Slowmo: {args.slowmo}ms")
    print(f"[DEBUG] Using locale: {locale} for {home_url}")
    print(f"Locale: {locale}")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless_mode,
            slow_mo=args.slowmo
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale=locale
        )
        
        page = await context.new_page()
        
        # Set timeouts (optimized for speed)
        page.set_default_timeout(10000)  # element wait: 10s max
        page.set_default_navigation_timeout(10000)  # navigation: 10s max
        
        try:
            navigator = Navigator(page, headless_mode, home_url)
            screenshot_manager = ScreenshotManager(args.out_dir, merchant_slug)
            report_generator = ReportGenerator(args.out_dir, merchant_slug)

            # --- Detection: attach network collector, goto home, collect signals, detect ---
            network_urls = attach_network_collector(page)
            await navigator.navigate_to_home(home_url)
            try:
                lang = await page.evaluate(
                    "() => document.documentElement.getAttribute('lang') || "
                    "(document.querySelector('meta[http-equiv=Content-Language]')?.getAttribute('content')) || ''"
                )
                if lang:
                    print(f"[DEBUG] Page lang: {lang}")
            except Exception:
                pass
            signals = await collect_page_signals(page)
            signals["network_requests_seen"] = list(network_urls)
            profile = detect(signals, home_url)
            detection_summary = {
                "platform": profile.platform,
                "psp": profile.psp,
                "confidence": profile.confidence,
                "evidence": profile.evidence,
            }
            print(f"[DETECTION] platform={profile.platform} psp={profile.psp} confidence={profile.confidence}")

            # --- Legacy checks (only when ENABLE_LEGACY_FOOTER_CHECKS=true) ---
            results = []
            skipped_checks = []
            if ENABLE_LEGACY_FOOTER_CHECKS:
                from auditor.legacy_checks import FooterKlarnaLogoCheck, PDPOSMCheck
                pdp_url = None
                if "jula.se" in home_url:
                    print("[DEBUG] jula.se: pdp_url left None so navigate_to_pdp will auto-pick PDP")
                else:
                    print("[DEBUG] navigate_to_pdp will auto-pick PDP if supported for this merchant")
                all_checks = [FooterKlarnaLogoCheck(), PDPOSMCheck()]
                if args.only:
                    only_id = (args.only or "").strip().upper()
                    if only_id == "FOOTER":
                        only_id = "FOOTER_KLARNA_LOGO"
                    checks = [c for c in all_checks if getattr(c, "CHECK_ID", "") == only_id]
                    if not checks:
                        print(f"[WARN] --only {args.only} did not match any check; available: FOOTER_KLARNA_LOGO, PDP_OSM")
                        checks = all_checks
                else:
                    checks = all_checks
                for check in checks:
                    try:
                        if isinstance(check, FooterKlarnaLogoCheck):
                            result = await check.execute(page, navigator, screenshot_manager, home_url)
                        elif isinstance(check, PDPOSMCheck):
                            result = await check.execute(page, navigator, screenshot_manager, pdp_url)
                        else:
                            continue
                        results.append(result)
                    except Exception as e:
                        print(f"[{check.CHECK_ID}] Exception: {str(e)}")
                        results.append(CheckResult(
                            check_id=check.CHECK_ID,
                            status="FAIL",
                            evidence=Evidence(),
                            timestamp=datetime.now().isoformat() + "Z",
                            error_reason=f"Exception: {str(e)}"
                        ))
            else:
                skipped_checks = [
                    {"check_id": "FOOTER_KLARNA_LOGO", "reason": "skipped: focus shifted to detection-only"},
                    {"check_id": "PDP_OSM", "reason": "skipped: focus shifted to detection-only"},
                ]

            report_path = report_generator.generate(
                results,
                detection_summary=detection_summary,
                skipped_checks=skipped_checks if skipped_checks else None,
            )
            
            print("\n" + "=" * 60)
            print("Audit Summary")
            print("=" * 60)
            print(f"Detection: platform={profile.platform} psp={profile.psp} confidence={profile.confidence}")
            if results:
                passed = sum(1 for r in results if r.status == "PASS")
                failed = sum(1 for r in results if r.status == "FAIL")
                print(f"Legacy checks: {len(results)} total, passed={passed}, failed={failed}")
            else:
                print("Legacy checks: skipped (ENABLE_LEGACY_FOOTER_CHECKS=false)")
            print(f"Report: {report_path}")
            print("=" * 60)
            
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
