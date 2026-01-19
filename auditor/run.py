"""
CLI entry point for Phase 0 auditor
"""
import argparse
import asyncio
import sys
from playwright.async_api import async_playwright
from auditor.checks.footer_klarna_logo import FooterKlarnaLogoCheck
from auditor.checks.pdp_osm import PDPOSMCheck
from auditor.checks.cart_klarna import CartKlarnaCheck
from auditor.checks.checkout_payment import CheckoutPaymentCheck
from auditor.navigator import Navigator
from auditor.screenshot import ScreenshotManager
from auditor.report import ReportGenerator, CheckResult, Evidence
from datetime import datetime


# Test URLs for humac.dk
HOME_URL = "https://www.humac.dk/"
PDP_URL = "https://www.humac.dk/produkter/headphones/airpods-pro-3"


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
        '--slowmo',
        type=int,
        default=0,
        help='Slow down operations by specified milliseconds (for debugging)'
    )
    parser.add_argument(
        '--locale',
        default='da-DK',
        help='Browser locale (default: da-DK)'
    )
    
    return parser.parse_args()


async def main():
    """Main execution function"""
    args = parse_args()
    
    print("=" * 60)
    print("Klarna Integration Auto Auditor - Phase 0")
    print("=" * 60)
    print(f"Output directory: {args.out_dir}")
    print(f"Headless: {args.headless}")
    print(f"Locale: {args.locale}")
    print("=" * 60)
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=args.headless,
            slow_mo=args.slowmo
        )
        
        # Create context with locale
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale=args.locale
        )
        
        page = await context.new_page()
        
        # Set timeouts (optimized for speed)
        page.set_default_timeout(10000)  # element wait: 10s max
        page.set_default_navigation_timeout(10000)  # navigation: 10s max
        
        try:
            # Initialize components
            navigator = Navigator(page, args.headless)
            screenshot_manager = ScreenshotManager(args.out_dir, "humac.dk")
            report_generator = ReportGenerator(args.out_dir, "humac.dk")
            
            # Initialize checks
            checks = [
                FooterKlarnaLogoCheck(),
                PDPOSMCheck(),
                CartKlarnaCheck(),
                CheckoutPaymentCheck()
            ]
            
            # Execute checks with error isolation
            results = []
            
            for check in checks:
                try:
                    if isinstance(check, FooterKlarnaLogoCheck):
                        result = await check.execute(
                            page, navigator, screenshot_manager, HOME_URL
                        )
                    elif isinstance(check, PDPOSMCheck):
                        result = await check.execute(
                            page, navigator, screenshot_manager, PDP_URL
                        )
                    elif isinstance(check, CartKlarnaCheck):
                        result = await check.execute(
                            page, navigator, screenshot_manager, HOME_URL
                        )
                    elif isinstance(check, CheckoutPaymentCheck):
                        result = await check.execute(
                            page, navigator, screenshot_manager, HOME_URL
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
