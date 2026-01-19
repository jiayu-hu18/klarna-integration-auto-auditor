"""
Core audit engine
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List
import logging

from app.data.merchant_loader import Merchant
from app.core.browser import BrowserManager
from app.detectors.footer_klarna_logo_detector import FooterKlarnaLogoDetector
from app.report.report_generator import AuditResult, ReportGenerator

logger = logging.getLogger(__name__)


class Auditor:
    """Core audit engine"""

    def __init__(self, headless: bool = True, timeout: int = 30000, max_retries: int = 2):
        """
        Initialize auditor
        
        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout in milliseconds
            max_retries: Maximum number of retries for failed audits
        """
        self.headless = headless
        self.timeout = timeout
        self.max_retries = max_retries
        self.detector = FooterKlarnaLogoDetector()

    async def audit_merchant(
        self,
        merchant: Merchant,
        screenshot_dir: str,
        retry_count: int = 0
    ) -> AuditResult:
        """
        Audit a single merchant
        
        Args:
            merchant: Merchant to audit
            screenshot_dir: Directory to save screenshots
            retry_count: Current retry attempt
            
        Returns:
            AuditResult object
        """
        browser = None
        timestamp = datetime.now().isoformat() + "Z"
        screenshot_path = None
        error = None

        try:
            # Initialize browser
            browser = BrowserManager(headless=self.headless, timeout=self.timeout)
            await browser.start()

            # Navigate to homepage
            logger.info(f"Auditing {merchant.merchant_name} ({merchant.merchant_id})")
            success = await browser.navigate(merchant.homepage_url, wait_time=3000)
            
            if not success:
                raise Exception(f"Failed to navigate to {merchant.homepage_url}")

            # Get page source
            page_source = await browser.get_page_source()

            # Run detection
            detection_result = await self.detector.detect(page_source, browser)

            # Capture screenshot
            screenshot_filename = f"{merchant.merchant_id}_{self.detector.RULE_ID}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            screenshot_path = str(Path(screenshot_dir) / screenshot_filename)
            await browser.capture_screenshot(screenshot_path)

            # Create audit result
            result = AuditResult(
                merchant_id=merchant.merchant_id,
                merchant_name=merchant.merchant_name,
                base_url=merchant.base_url,
                audit_status="completed",
                audit_timestamp=timestamp,
                rule_id=self.detector.RULE_ID,
                rule_description="Detect Klarna logo in footer",
                passed=detection_result.passed,
                confidence=detection_result.confidence,
                matched_selectors=detection_result.matched_selectors,
                screenshot_path=screenshot_path,
                message=detection_result.message,
                error=None
            )

            logger.info(f"Completed audit for {merchant.merchant_name}: {'PASSED' if result.passed else 'FAILED'}")
            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error auditing {merchant.merchant_name}: {error_msg}")
            
            # Retry logic
            if retry_count < self.max_retries:
                logger.info(f"Retrying {merchant.merchant_name} (attempt {retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(2)  # Wait before retry
                return await self.audit_merchant(merchant, screenshot_dir, retry_count + 1)

            # Return failed result
            return AuditResult(
                merchant_id=merchant.merchant_id,
                merchant_name=merchant.merchant_name,
                base_url=merchant.base_url,
                audit_status="failed",
                audit_timestamp=timestamp,
                rule_id=self.detector.RULE_ID,
                rule_description="Detect Klarna logo in footer",
                passed=False,
                confidence=0.0,
                matched_selectors=[],
                screenshot_path=screenshot_path,
                message=f"Audit failed: {error_msg}",
                error=error_msg
            )

        finally:
            if browser:
                await browser.close()

    async def audit_all(
        self,
        merchants: List[Merchant],
        screenshot_dir: str
    ) -> List[AuditResult]:
        """
        Audit all merchants
        
        Args:
            merchants: List of merchants to audit
            screenshot_dir: Directory to save screenshots
            
        Returns:
            List of AuditResult objects
        """
        results = []
        
        # Create screenshot directory
        Path(screenshot_dir).mkdir(parents=True, exist_ok=True)

        for merchant in merchants:
            try:
                result = await self.audit_merchant(merchant, screenshot_dir)
                results.append(result)
            except Exception as e:
                logger.error(f"Unexpected error processing {merchant.merchant_id}: {e}")
                # Create error result
                results.append(AuditResult(
                    merchant_id=merchant.merchant_id,
                    merchant_name=merchant.merchant_name,
                    base_url=merchant.base_url,
                    audit_status="failed",
                    audit_timestamp=datetime.now().isoformat() + "Z",
                    rule_id=self.detector.RULE_ID,
                    rule_description="Detect Klarna logo in footer",
                    passed=False,
                    confidence=0.0,
                    matched_selectors=[],
                    screenshot_path=None,
                    message=f"Unexpected error: {str(e)}",
                    error=str(e)
                ))

        return results
