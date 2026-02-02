"""
CLI entry point for Phase 0 auditor
"""
import argparse
import asyncio
import sys
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from auditor.checks.footer_klarna_logo import FooterKlarnaLogoCheck
from auditor.checks.pdp_osm import PDPOSMCheck
from auditor.checks.cart_klarna import CartKlarnaCheck
from auditor.checks.checkout_payment import CheckoutPaymentCheck
from auditor.navigator import Navigator
from auditor.screenshot import ScreenshotManager
from auditor.report import ReportGenerator, CheckResult, Evidence
from datetime import datetime


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
            headless=False,
            slow_mo=300
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
            # Initialize components
            navigator = Navigator(page, headless_mode, home_url)
            screenshot_manager = ScreenshotManager(args.out_dir, merchant_slug)
            report_generator = ReportGenerator(args.out_dir, merchant_slug)

            # Optional: load home once and read page lang for logging (can be used to suggest locale)
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

            # PDP URL: jula.se auto-picks from /erbjudanden/; others may need auto-pick or None
            pdp_url = None
            if "jula.se" in home_url:
                print("[DEBUG] jula.se: pdp_url left None so navigate_to_pdp will auto-pick PDP")
            else:
                print("[DEBUG] navigate_to_pdp will auto-pick PDP if supported for this merchant")

            # Initialize checks (only FOOTER + PDP_OSM for jula.se test)
            checks = [
                FooterKlarnaLogoCheck(),
                PDPOSMCheck(),
                # CartKlarnaCheck(),
                # CheckoutPaymentCheck()
            ]
            
            # Execute checks with error isolation
            results = []
            
            for check in checks:
                try:
                    if isinstance(check, FooterKlarnaLogoCheck):
                        result = await check.execute(
                            page, navigator, screenshot_manager, home_url
                        )
                    elif isinstance(check, PDPOSMCheck):
                        result = await check.execute(
                            page, navigator, screenshot_manager, pdp_url
                        )
                    elif isinstance(check, CartKlarnaCheck):
                        result = await check.execute(
                            page, navigator, screenshot_manager, home_url
                        )
                    elif isinstance(check, CheckoutPaymentCheck):
                        result = await check.execute(
                            page, navigator, screenshot_manager, home_url
                        )
                    else:
                        continue
                    
                    results.append(result)
                    
                except Exception as e:
                    # Error isolation: continue with next check
                    print(f"[{check.CHECK_ID}] Exception occurred: {str(e)}")
                    results.append(CheckResult(
                        check_id=check.CHECK_ID,
                        status="FAIL",
                        evidence=Evidence(),
                        timestamp=datetime.now().isoformat() + "Z",
                        error_reason=f"Exception: {str(e)}"
                    ))
            
            # Generate report
            report_path = report_generator.generate(results)
            
            print("\n" + "=" * 60)
            print("Audit Summary")
            print("=" * 60)
            passed = sum(1 for r in results if r.status == "PASS")
            failed = sum(1 for r in results if r.status == "FAIL")
            print(f"Total checks: {len(results)}")
            print(f"Passed: {passed}")
            print(f"Failed: {failed}")
            print(f"Report: {report_path}")
            print("=" * 60)
            
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
