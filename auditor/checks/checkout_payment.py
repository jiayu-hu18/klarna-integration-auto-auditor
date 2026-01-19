"""
Check 4: CHECKOUT_PAYMENT_POSITION
"""
from datetime import datetime
from typing import Tuple, List, Optional
from playwright.async_api import Page, ElementHandle
from auditor.navigator import Navigator
from auditor.screenshot import ScreenshotManager
from auditor.report import CheckResult, Evidence
from auditor.data.address_manager import AddressManager
from auditor.utils import detect_country_from_url


class CheckoutPaymentCheck:
    """Check 4: CHECKOUT_PAYMENT_POSITION"""
    
    CHECK_ID = "CHECKOUT_PAYMENT_POSITION"
    PAYMENT_SELECTORS = [
        'input[name="payment_method"]',
        '.payment-options',
        '.payment-methods',
        '[data-payment-method]',
        '.payment-method',
        'label[for*="payment"]',
        '[class*="payment-option"]',
        '[class*="payment-method"]'
    ]
    
    async def execute(
        self,
        page: Page,
        navigator: Navigator,
        screenshot_manager: ScreenshotManager,
        base_url: str
    ) -> CheckResult:
        """Execute checkout payment position check"""
        try:
            print(f"[{self.CHECK_ID}] Starting check...")
            
            # 1. Navigate to checkout (assumes we're on cart)
            success, error_msg = await navigator.navigate_to_checkout()
            if not success:
                # Capture error screenshot
                screenshot_path = await screenshot_manager.capture_checkout_payment(page)
                print(f"[{self.CHECK_ID}] FAIL - Cannot reach checkout: {error_msg}")
                print(f"[{self.CHECK_ID}] Screenshot: {screenshot_path}")
                return CheckResult(
                    check_id=self.CHECK_ID,
                    status="FAIL",
                    evidence=Evidence(screenshot_path=screenshot_path),
                    timestamp=datetime.now().isoformat() + "Z",
                    error_reason=error_msg,
                    payment_methods=[],
                    klarna_index=None
                )
            
            # 2. Fill test address if needed
            await self.fill_test_address_if_needed(page, base_url)
            
            # 3. Wait for payment methods
            ready = await self.wait_for_payment_methods(page, navigator)
            if not ready:
                screenshot_path = await screenshot_manager.capture_checkout_payment(page)
                print(f"[{self.CHECK_ID}] FAIL - Payment methods not loaded")
                print(f"[{self.CHECK_ID}] Screenshot: {screenshot_path}")
                return CheckResult(
                    check_id=self.CHECK_ID,
                    status="FAIL",
                    evidence=Evidence(screenshot_path=screenshot_path),
                    timestamp=datetime.now().isoformat() + "Z",
                    error_reason="Payment methods not loaded",
                    payment_methods=[],
                    klarna_index=None
                )
            
            # 4. Collect payment methods
            payment_methods = await self.collect_payment_methods(page)
            
            # 5. Find Klarna position
            klarna_index = await self.find_klarna_position(payment_methods)
            
            # 6. Capture screenshot
            payment_element = await self.find_payment_methods_element(page)
            screenshot_path = await screenshot_manager.capture_checkout_payment(page, payment_element)
            
            # 7. Build evidence
            matched_text = f"Payment method at position {klarna_index}" if klarna_index else None
            evidence = Evidence(
                screenshot_path=screenshot_path,
                matched_text=matched_text
            )
            
            status = "PASS" if klarna_index else "FAIL"
            error_reason = None if klarna_index else "Klarna not found in payment methods"
            
            print(f"[{self.CHECK_ID}] {status} - Screenshot: {screenshot_path}")
            print(f"[{self.CHECK_ID}] Payment methods: {payment_methods}")
            print(f"[{self.CHECK_ID}] Klarna index: {klarna_index}")
            if error_reason:
                print(f"[{self.CHECK_ID}] Error: {error_reason}")
            
            return CheckResult(
                check_id=self.CHECK_ID,
                status=status,
                evidence=evidence,
                timestamp=datetime.now().isoformat() + "Z",
                error_reason=error_reason,
                payment_methods=payment_methods,
                klarna_index=klarna_index
            )
            
        except Exception as e:
            print(f"[{self.CHECK_ID}] Exception: {str(e)}")
            screenshot_path = await screenshot_manager.capture_checkout_payment(page)
            return CheckResult(
                check_id=self.CHECK_ID,
                status="FAIL",
                evidence=Evidence(screenshot_path=screenshot_path),
                timestamp=datetime.now().isoformat() + "Z",
                error_reason=f"Exception: {str(e)}",
                payment_methods=[],
                klarna_index=None
            )
    
    async def fill_test_address_if_needed(self, page: Page, base_url: str) -> bool:
        """Fill test address if address form is present"""
        # Check if address form exists
        address_indicators = [
            'input[name*="address"]',
            'input[name*="street"]',
            'input[name*="postal"]',
            'input[name*="zip"]',
            'input[name*="city"]'
        ]
        
        has_address_form = False
        for indicator in address_indicators:
            try:
                if await page.query_selector(indicator):
                    has_address_form = True
                    break
            except Exception:
                continue
        
        if not has_address_form:
            return True  # No address form needed
        
        # Get address from address manager
        try:
            country_code = detect_country_from_url(base_url) or "DK"
            address_manager = AddressManager()
            address = address_manager.get_address(country_code)
            
            if not address:
                print(f"[{self.CHECK_ID}] Warning: No test address found for {country_code}")
                return False
            
            # Fill address fields
            field_mappings = {
                'first_name': ['firstname', 'first_name', 'fname'],
                'last_name': ['lastname', 'last_name', 'lname'],
                'email': ['email', 'e-mail'],
                'phone': ['phone', 'telephone', 'tel'],
                'street': ['street', 'address1', 'address_line1'],
                'postal_code': ['postal', 'postcode', 'zip', 'zipcode'],
                'city': ['city'],
                'region': ['region', 'state', 'province']
            }
            
            filled = False
            for attr, field_names in field_mappings.items():
                value = getattr(address, attr, None)
                if not value:
                    continue
                
                for field_name in field_names:
                    selectors = [
                        f'input[name="{field_name}"]',
                        f'input[name*="{field_name}"]',
                        f'input[id*="{field_name}"]'
                    ]
                    
                    for selector in selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element:
                                await element.fill(str(value))
                                filled = True
                                break
                        except Exception:
                            continue
                    if filled:
                        break
            
            if filled:
                await page.wait_for_timeout(300)  # Minimal wait for form validation
            
            return True
            
        except Exception as e:
            print(f"[{self.CHECK_ID}] Warning: Address fill failed: {str(e)}")
            return False
    
    async def wait_for_payment_methods(self, page: Page, navigator: Navigator) -> bool:
        """Wait for payment methods to be visible"""
        # Wait for DOM content loaded (faster)
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=5000)
        except Exception:
            pass
        
        # Try payment selectors (reduced timeout)
        for selector in self.PAYMENT_SELECTORS:
            try:
                await page.wait_for_selector(selector, timeout=3000, state='visible')
                return True
            except Exception:
                continue
        
        return False
    
    async def find_payment_methods_element(self, page: Page) -> Optional[ElementHandle]:
        """Find payment methods container element"""
        for selector in self.PAYMENT_SELECTORS:
            try:
                element = await page.query_selector(selector)
                if element:
                    # Try to find parent container
                    parent = await element.evaluate_handle('el => el.closest(".payment-options, .payment-methods, [class*=\"payment\"]")')
                    if parent:
                        return parent.as_element()
                    return element
            except Exception:
                continue
        
        return None
    
    async def collect_payment_methods(self, page: Page) -> List[str]:
        """Collect all visible payment method labels"""
        payment_methods = []
        
        # Try different strategies to find payment methods
        strategies = [
            # Strategy 1: Radio buttons with labels
            lambda: page.query_selector_all('input[type="radio"][name*="payment"] + label'),
            # Strategy 2: Labels with for attributes
            lambda: page.query_selector_all('label[for*="payment"]'),
            # Strategy 3: Elements with payment class
            lambda: page.query_selector_all('[class*="payment-method"]'),
            # Strategy 4: Payment option containers
            lambda: page.query_selector_all('[class*="payment-option"]'),
        ]
        
        for strategy in strategies:
            try:
                elements = await strategy()
                if elements:
                    for element in elements:
                        try:
                            text = await element.inner_text()
                            text = text.strip()
                            if text and text not in payment_methods:
                                payment_methods.append(text)
                        except Exception:
                            continue
                    
                    if payment_methods:
                        break
            except Exception:
                continue
        
        # Fallback: search for payment-related text
        if not payment_methods:
            try:
                page_text = await page.text_content()
                # Look for common payment method patterns
                import re
                # This is a simple fallback - could be improved
                payment_keywords = ['credit card', 'klarna', 'paypal', 'visa', 'mastercard']
                for keyword in payment_keywords:
                    if keyword.lower() in page_text.lower():
                        payment_methods.append(keyword.title())
            except Exception:
                pass
        
        return payment_methods
    
    async def find_klarna_position(self, payment_methods: List[str]) -> Optional[int]:
        """
        Find Klarna position in payment methods list (1-based)
        Case-insensitive contains("klarna") match
        """
        for i, method in enumerate(payment_methods, start=1):
            if 'klarna' in method.lower():
                return i
        
        return None
