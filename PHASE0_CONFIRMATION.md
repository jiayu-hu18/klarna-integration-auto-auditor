# Phase 0 Implementation Confirmation - Single Merchant Audit

## 1. Project Scope

**Target**: Single merchant (humac.dk) automatic audit script  
**Purpose**: Verify Klarna Best Practice minimum closed loop  
**Scope**: No batch processing, no internal APIs

## 2. Test Targets

- **HOME**: `https://www.humac.dk/`
- **PDP**: `https://www.humac.dk/produkter/headphones/airpods-pro-3?recombee_recomm_id=5a359d9160d4d4d5fa56d9ae440610ad&utm_content=personlig&utm_source=forside&_gl=1*kloaqj*_up*MQ..*_ga*MTg2NTI5MTgyMy4xNzY4ODM0MjMz*_ga_M97C156RML*czE3Njg4MzQyMzIkbzEkZzAkdDE3Njg4MzQyMzIkajYwJGwwJGgw`
- **CART**: `https://www.humac.dk/cart` (navigated from PDP after adding to cart)
- **CHECKOUT**: Navigated from CART by clicking checkout button

## 3. Directory Structure

```
klarna-integration-auto-auditor/
├── auditor/
│   ├── __init__.py
│   ├── run.py                    # CLI entry point
│   ├── navigator.py             # Page navigation logic
│   ├── checks/
│   │   ├── __init__.py
│   │   ├── footer_klarna_logo.py    # Check 1
│   │   ├── pdp_osm.py               # Check 2
│   │   ├── cart_klarna.py            # Check 3
│   │   └── checkout_payment.py      # Check 4
│   ├── screenshot.py            # Screenshot management
│   ├── report.py                # JSON report generation
│   └── utils.py                 # Cookie banner handler, etc.
├── tests/
│   └── test_auditor.py          # Integration tests
├── requirements.txt
└── README.md
```

## 4. Core Module Function Signatures

### 4.1 auditor/run.py - CLI Entry Point

```python
def main():
    """
    Main entry point
    Parse CLI arguments and orchestrate audit
    """
    pass

def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments
    
    Returns:
        Namespace with: out_dir, headless
    """
    pass
```

### 4.2 auditor/navigator.py - Page Navigation

```python
class Navigator:
    """Handle page navigation and flow"""
    
    def __init__(self, page: Page, headless: bool = True):
        """
        Initialize navigator
        
        Args:
            page: Playwright page object
            headless: Whether running in headless mode
        """
        pass
    
    async def navigate_to_home(self) -> bool:
        """
        Navigate to HOME page
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    async def navigate_to_pdp(self, pdp_url: str) -> bool:
        """
        Navigate to PDP page
        
        Args:
            pdp_url: Product detail page URL
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    async def add_to_cart(self) -> bool:
        """
        Click add to cart button on PDP
        Try multiple common selectors
        
        Returns:
            True if clicked successfully, False otherwise
        """
        pass
    
    async def navigate_to_cart(self) -> bool:
        """
        Navigate to cart page (after adding to cart)
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    async def navigate_to_checkout(self) -> Tuple[bool, Optional[str]]:
        """
        Click checkout button and navigate to checkout
        
        Returns:
            Tuple of (success, error_message)
            error_message is None if successful, otherwise contains reason
        """
        pass
    
    async def handle_cookie_banner(self) -> None:
        """
        Try to handle cookie banner (click Accept/OK)
        Non-blocking: failures are ignored
        """
        pass
    
    async def wait_for_page_ready(
        self,
        selectors: List[str] = None,
        fallback_keywords: List[str] = None,
        timeout: int = 10000
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Wait for page to be ready
        Strategy: networkidle + selector wait + keyword fallback
        
        Args:
            selectors: List of selectors to wait for
            fallback_keywords: Keywords to search if selectors fail
            timeout: Timeout in milliseconds
            
        Returns:
            Tuple of (success, matched_selector, matched_keyword)
        """
        pass
```

### 4.3 auditor/checks/footer_klarna_logo.py - Check 1

```python
class FooterKlarnaLogoCheck:
    """Check 1: FOOTER_KLARNA_LOGO"""
    
    CHECK_ID = "FOOTER_KLARNA_LOGO"
    
    async def execute(
        self,
        page: Page,
        navigator: Navigator,
        screenshot_manager: ScreenshotManager
    ) -> CheckResult:
        """
        Execute footer Klarna logo check
        
        Steps:
        1. Navigate to HOME
        2. Wait for page ready
        3. Find footer element
        4. Check for Klarna logo (img src/alt or text)
        5. Capture footer screenshot
        6. Return result
        
        Returns:
            CheckResult with status, evidence, timestamp
        """
        pass
    
    async def detect_klarna_in_footer(
        self,
        page: Page
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Detect Klarna logo in footer
        
        Returns:
            Tuple of (found, matched_selector, matched_text)
        """
        pass
    
    async def find_footer_element(
        self,
        page: Page
    ) -> Optional[ElementHandle]:
        """
        Find footer element (check main frame and iframes)
        
        Returns:
            Footer element or None
        """
        pass
```

### 4.4 auditor/checks/pdp_osm.py - Check 2

```python
class PDPOSMCheck:
    """Check 2: PDP_OSM"""
    
    CHECK_ID = "PDP_OSM"
    KEYWORDS = ["Klarna", "Del op", "Kort", "Klarna Pay", "Klarna logo"]
    
    async def execute(
        self,
        page: Page,
        navigator: Navigator,
        screenshot_manager: ScreenshotManager,
        pdp_url: str
    ) -> CheckResult:
        """
        Execute PDP OSM check
        
        Steps:
        1. Navigate to PDP
        2. Wait for price and buy button
        3. Search for OSM keywords in page content
        4. Capture OSM/price area screenshot
        5. Return result
        
        Returns:
            CheckResult with status, evidence, timestamp
        """
        pass
    
    async def detect_osm_keywords(
        self,
        page: Page
    ) -> Tuple[bool, List[str]]:
        """
        Detect OSM keywords in page content
        
        Returns:
            Tuple of (found, list of matched keywords)
        """
        pass
    
    async def wait_for_pdp_ready(
        self,
        page: Page,
        navigator: Navigator
    ) -> bool:
        """
        Wait for PDP to be ready (price and buy button visible)
        
        Returns:
            True if ready, False if timeout
        """
        pass
```

### 4.5 auditor/checks/cart_klarna.py - Check 3

```python
class CartKlarnaCheck:
    """Check 3: CART_KLARNA"""
    
    CHECK_ID = "CART_KLARNA"
    
    async def execute(
        self,
        page: Page,
        navigator: Navigator,
        screenshot_manager: ScreenshotManager
    ) -> CheckResult:
        """
        Execute cart Klarna check
        
        Steps:
        1. Ensure we're on PDP (from previous check)
        2. Click add to cart
        3. Navigate to cart
        4. Wait for cart to load
        5. Search for "Klarna" keyword
        6. Capture cart summary area screenshot (or full page)
        7. Return result
        
        Returns:
            CheckResult with status, evidence, timestamp
        """
        pass
    
    async def detect_klarna_in_cart(
        self,
        page: Page
    ) -> Tuple[bool, Optional[str]]:
        """
        Detect Klarna keyword in cart page
        
        Returns:
            Tuple of (found, matched_text)
        """
        pass
    
    async def find_cart_summary_area(
        self,
        page: Page
    ) -> Optional[ElementHandle]:
        """
        Find cart summary area for screenshot
        
        Returns:
            Cart summary element or None (will use full page)
        """
        pass
```

### 4.6 auditor/checks/checkout_payment.py - Check 4

```python
class CheckoutPaymentCheck:
    """Check 4: CHECKOUT_PAYMENT_POSITION"""
    
    CHECK_ID = "CHECKOUT_PAYMENT_POSITION"
    PAYMENT_SELECTORS = [
        'input[name="payment_method"]',
        '.payment-options',
        '.payment-methods',
        '[data-payment-method]',
        '.payment-method',
        'label[for*="payment"]'
    ]
    
    async def execute(
        self,
        page: Page,
        navigator: Navigator,
        screenshot_manager: ScreenshotManager
    ) -> CheckResult:
        """
        Execute checkout payment position check
        
        Steps:
        1. Ensure we're on cart (from previous check)
        2. Click checkout button
        3. Handle address form if needed (use test address)
        4. Wait for payment methods to load
        5. Collect all payment method labels
        6. Find Klarna position (1-based index)
        7. Capture payment methods area screenshot
        8. Return result
        
        Returns:
            CheckResult with status, evidence, timestamp, payment_methods, klarna_index
        """
        pass
    
    async def navigate_to_checkout(
        self,
        page: Page,
        navigator: Navigator
    ) -> Tuple[bool, Optional[str]]:
        """
        Navigate to checkout from cart
        
        Returns:
            Tuple of (success, error_message)
        """
        pass
    
    async def fill_test_address_if_needed(
        self,
        page: Page
    ) -> bool:
        """
        Fill test address if address form is present
        
        Returns:
            True if filled or not needed, False if failed
        """
        pass
    
    async def wait_for_payment_methods(
        self,
        page: Page,
        navigator: Navigator
    ) -> bool:
        """
        Wait for payment methods to be visible
        
        Returns:
            True if loaded, False if timeout
        """
        pass
    
    async def collect_payment_methods(
        self,
        page: Page
    ) -> List[str]:
        """
        Collect all visible payment method labels
        
        Returns:
            List of payment method text labels
        """
        pass
    
    async def find_klarna_position(
        self,
        payment_methods: List[str]
    ) -> Optional[int]:
        """
        Find Klarna position in payment methods list (1-based)
        Case-insensitive contains("klarna") match
        
        Args:
            payment_methods: List of payment method labels
            
        Returns:
            Position index (1-based) or None if not found
        """
        pass
```

### 4.7 auditor/screenshot.py - Screenshot Management

```python
class ScreenshotManager:
    """Manage screenshots for audit"""
    
    def __init__(self, out_dir: str, merchant: str = "humac.dk"):
        """
        Initialize screenshot manager
        
        Args:
            out_dir: Base output directory
            merchant: Merchant identifier
        """
        pass
    
    def get_screenshot_path(self, page_type: str) -> str:
        """
        Generate screenshot path: {out_dir}/{merchant}/{page_type}_{yyyyMMdd_HHmmss}.png
        
        Args:
            page_type: Type of page (footer, pdp_osm, cart, checkout_payment)
            
        Returns:
            Full path to screenshot file
        """
        pass
    
    async def capture_footer(
        self,
        page: Page,
        footer_element: Optional[ElementHandle] = None
    ) -> str:
        """
        Capture footer screenshot
        
        Args:
            page: Playwright page object
            footer_element: Optional footer element (if None, captures full page)
            
        Returns:
            Path to saved screenshot
        """
        pass
    
    async def capture_pdp_osm(
        self,
        page: Page
    ) -> str:
        """Capture PDP OSM/price area screenshot"""
        pass
    
    async def capture_cart(
        self,
        page: Page,
        cart_summary_element: Optional[ElementHandle] = None
    ) -> str:
        """
        Capture cart screenshot
        
        Args:
            page: Playwright page object
            cart_summary_element: Optional cart summary element
            
        Returns:
            Path to saved screenshot
        """
        pass
    
    async def capture_checkout_payment(
        self,
        page: Page,
        payment_methods_element: Optional[ElementHandle] = None
    ) -> str:
        """
        Capture checkout payment methods screenshot
        
        Args:
            page: Playwright page object
            payment_methods_element: Optional payment methods element
            
        Returns:
            Path to saved screenshot
        """
        pass
```

### 4.8 auditor/report.py - Report Generation

```python
@dataclass
class CheckResult:
    """Result of a single check"""
    check_id: str
    status: str  # "PASS" | "FAIL"
    evidence: Evidence
    timestamp: str
    error: Optional[str] = None
    # For CHECKOUT_PAYMENT_POSITION only:
    payment_methods: Optional[List[str]] = None
    klarna_index: Optional[int] = None

@dataclass
class Evidence:
    """Evidence for a check result"""
    screenshot_path: Optional[str] = None
    matched_selector: Optional[str] = None
    matched_text: Optional[str] = None

class ReportGenerator:
    """Generate JSON report"""
    
    def __init__(self, out_dir: str, merchant: str = "humac.dk"):
        """
        Initialize report generator
        
        Args:
            out_dir: Output directory
            merchant: Merchant identifier
        """
        pass
    
    def generate(self, results: List[CheckResult]) -> str:
        """
        Generate JSON report
        
        Args:
            results: List of check results
            
        Returns:
            Path to generated report file (out/{merchant}/report.json)
        """
        pass
    
    def _format_result(self, result: CheckResult) -> Dict[str, Any]:
        """Format single check result to JSON"""
        pass
```

### 4.9 auditor/utils.py - Utility Functions

```python
async def handle_cookie_banner(page: Page) -> None:
    """
    Try to handle cookie banner (click Accept/OK)
    Non-blocking: failures are ignored
    
    Common selectors to try:
    - button[class*="accept"]
    - button[class*="cookie"]
    - button[id*="accept"]
    - #cookie-accept
    - .cookie-accept
    """
    pass

async def get_element_snippet_and_path(
    page: Page,
    element: ElementHandle
) -> Dict[str, str]:
    """
    Get DOM snippet (innerHTML) and selector path (xpath/CSS path)
    
    Args:
        page: Playwright page object
        element: Element handle
        
    Returns:
        Dictionary with 'snippet' and 'path'
    """
    pass

async def find_element_in_frames(
    page: Page,
    selector: str
) -> Tuple[Optional[ElementHandle], Optional[Frame]]:
    """
    Find element, checking iframe frames if not found in main frame
    
    Args:
        page: Playwright page object
        selector: CSS selector
        
    Returns:
        Tuple of (element, frame) or (None, None) if not found
    """
    pass

def detect_country_from_url(url: str) -> Optional[str]:
    """
    Detect country code from URL
    
    Examples:
    - .dk -> DK
    - .se -> SE
    - .no -> NO
    
    Returns:
        Country code or None
    """
    pass
```

## 5. Execution Flow Pseudo-code

### 5.1 Main Execution Flow

```python
async def main():
    # 1. Parse CLI arguments
    args = parse_args()
    out_dir = args.out_dir
    headless = args.headless
    
    # 2. Initialize Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        # Set timeouts
        page.set_default_timeout(30000)  # navigation
        page.set_default_navigation_timeout(30000)
        
        try:
            # 3. Initialize components
            navigator = Navigator(page, headless)
            screenshot_manager = ScreenshotManager(out_dir, "humac.dk")
            report_generator = ReportGenerator(out_dir, "humac.dk")
            
            # 4. Initialize checks
            checks = [
                FooterKlarnaLogoCheck(),
                PDPOSMCheck(),
                CartKlarnaCheck(),
                CheckoutPaymentCheck()
            ]
            
            # 5. Execute checks with error isolation
            results = []
            for check in checks:
                try:
                    result = await check.execute(
                        page, navigator, screenshot_manager, pdp_url
                    )
                    results.append(result)
                except Exception as e:
                    # Error isolation: continue with next check
                    results.append(CheckResult(
                        check_id=check.CHECK_ID,
                        status="FAIL",
                        evidence=Evidence(),
                        timestamp=datetime.now().isoformat() + "Z",
                        error=str(e)
                    ))
            
            # 6. Generate report
            report_path = report_generator.generate(results)
            print(f"Report saved to: {report_path}")
            
        finally:
            await browser.close()
```

### 5.2 Check 1: FOOTER_KLARNA_LOGO Flow

```python
async def execute():
    try:
        # 1. Navigate to HOME
        success = await navigator.navigate_to_home()
        if not success:
            return CheckResult(status="FAIL", error="Navigation failed")
        
        # 2. Handle cookie banner (non-blocking)
        await navigator.handle_cookie_banner()
        
        # 3. Wait for page ready
        ready, selector, keyword = await navigator.wait_for_page_ready(
            selectors=['footer', '[class*="footer"]'],
            timeout=10000
        )
        
        # 4. Find footer element (check frames)
        footer = await find_footer_element(page)
        
        # 5. Detect Klarna in footer
        found, matched_selector, matched_text = await detect_klarna_in_footer(page)
        
        # 6. Capture screenshot
        screenshot_path = await screenshot_manager.capture_footer(page, footer)
        
        # 7. Build evidence
        evidence = Evidence(
            screenshot_path=screenshot_path,
            matched_selector=matched_selector,
            matched_text=matched_text
        )
        
        return CheckResult(
            check_id="FOOTER_KLARNA_LOGO",
            status="PASS" if found else "FAIL",
            evidence=evidence,
            timestamp=datetime.now().isoformat() + "Z"
        )
        
    except Exception as e:
        return CheckResult(
            check_id="FOOTER_KLARNA_LOGO",
            status="FAIL",
            evidence=Evidence(),
            timestamp=datetime.now().isoformat() + "Z",
            error=str(e)
        )
```

### 5.3 Check 2: PDP_OSM Flow

```python
async def execute(pdp_url):
    try:
        # 1. Navigate to PDP
        success = await navigator.navigate_to_pdp(pdp_url)
        if not success:
            return CheckResult(status="FAIL", error="PDP navigation failed")
        
        # 2. Handle cookie banner
        await navigator.handle_cookie_banner()
        
        # 3. Wait for PDP ready (price and buy button)
        ready = await wait_for_pdp_ready(page, navigator)
        if not ready:
            return CheckResult(status="FAIL", error="PDP not ready")
        
        # 4. Detect OSM keywords
        found, matched_keywords = await detect_osm_keywords(page)
        
        # 5. Capture screenshot
        screenshot_path = await screenshot_manager.capture_pdp_osm(page)
        
        # 6. Build evidence
        evidence = Evidence(
            screenshot_path=screenshot_path,
            matched_text=", ".join(matched_keywords) if matched_keywords else None
        )
        
        return CheckResult(
            check_id="PDP_OSM",
            status="PASS" if found else "FAIL",
            evidence=evidence,
            timestamp=datetime.now().isoformat() + "Z"
        )
        
    except Exception as e:
        return CheckResult(
            check_id="PDP_OSM",
            status="FAIL",
            evidence=Evidence(),
            timestamp=datetime.now().isoformat() + "Z",
            error=str(e)
        )
```

### 5.4 Check 3: CART_KLARNA Flow

```python
async def execute():
    try:
        # 1. Click add to cart (assumes we're on PDP from previous check)
        success = await navigator.add_to_cart()
        if not success:
            return CheckResult(status="FAIL", error="Add to cart button not found")
        
        # 2. Navigate to cart
        success = await navigator.navigate_to_cart()
        if not success:
            return CheckResult(status="FAIL", error="Cart navigation failed")
        
        # 3. Wait for cart to load
        ready, _, _ = await navigator.wait_for_page_ready(
            selectors=['[class*="cart"]', '[id*="cart"]'],
            timeout=10000
        )
        
        # 4. Detect Klarna in cart
        found, matched_text = await detect_klarna_in_cart(page)
        
        # 5. Find cart summary area (optional)
        cart_summary = await find_cart_summary_area(page)
        
        # 6. Capture screenshot
        screenshot_path = await screenshot_manager.capture_cart(page, cart_summary)
        
        # 7. Build evidence
        evidence = Evidence(
            screenshot_path=screenshot_path,
            matched_text=matched_text
        )
        
        return CheckResult(
            check_id="CART_KLARNA",
            status="PASS" if found else "FAIL",
            evidence=evidence,
            timestamp=datetime.now().isoformat() + "Z"
        )
        
    except Exception as e:
        return CheckResult(
            check_id="CART_KLARNA",
            status="FAIL",
            evidence=Evidence(),
            timestamp=datetime.now().isoformat() + "Z",
            error=str(e)
        )
```

### 5.5 Check 4: CHECKOUT_PAYMENT_POSITION Flow

```python
async def execute():
    try:
        # 1. Navigate to checkout (assumes we're on cart)
        success, error_msg = await navigate_to_checkout(page, navigator)
        if not success:
            # Capture error screenshot
            screenshot_path = await screenshot_manager.capture_checkout_payment(page)
            return CheckResult(
                check_id="CHECKOUT_PAYMENT_POSITION",
                status="FAIL",
                evidence=Evidence(screenshot_path=screenshot_path),
                timestamp=datetime.now().isoformat() + "Z",
                error=error_msg,
                payment_methods=[],
                klarna_index=None
            )
        
        # 2. Fill test address if needed
        await fill_test_address_if_needed(page)
        
        # 3. Wait for payment methods
        ready = await wait_for_payment_methods(page, navigator)
        if not ready:
            screenshot_path = await screenshot_manager.capture_checkout_payment(page)
            return CheckResult(
                check_id="CHECKOUT_PAYMENT_POSITION",
                status="FAIL",
                evidence=Evidence(screenshot_path=screenshot_path),
                timestamp=datetime.now().isoformat() + "Z",
                error="Payment methods not loaded",
                payment_methods=[],
                klarna_index=None
            )
        
        # 4. Collect payment methods
        payment_methods = await collect_payment_methods(page)
        
        # 5. Find Klarna position
        klarna_index = await find_klarna_position(payment_methods)
        
        # 6. Capture screenshot
        screenshot_path = await screenshot_manager.capture_checkout_payment(page)
        
        # 7. Build evidence
        evidence = Evidence(
            screenshot_path=screenshot_path,
            matched_text=f"Payment method at position {klarna_index}" if klarna_index else None
        )
        
        return CheckResult(
            check_id="CHECKOUT_PAYMENT_POSITION",
            status="PASS" if klarna_index else "FAIL",
            evidence=evidence,
            timestamp=datetime.now().isoformat() + "Z",
            payment_methods=payment_methods,
            klarna_index=klarna_index
        )
        
    except Exception as e:
        screenshot_path = await screenshot_manager.capture_checkout_payment(page)
        return CheckResult(
            check_id="CHECKOUT_PAYMENT_POSITION",
            status="FAIL",
            evidence=Evidence(screenshot_path=screenshot_path),
            timestamp=datetime.now().isoformat() + "Z",
            error=str(e),
            payment_methods=[],
            klarna_index=None
        )
```

## 6. JSON Report Schema

```json
{
  "merchant": "humac.dk",
  "run_id": "20260119_150000",
  "timestamp": "2026-01-19T15:00:00Z",
  "results": [
    {
      "check_id": "FOOTER_KLARNA_LOGO",
      "status": "PASS",
      "evidence": {
        "screenshot_path": "out/humac.dk/footer_20260119_150030.png",
        "matched_selector": "footer img[src*='klarna']",
        "matched_text": null
      },
      "timestamp": "2026-01-19T15:00:30Z"
    },
    {
      "check_id": "PDP_OSM",
      "status": "PASS",
      "evidence": {
        "screenshot_path": "out/humac.dk/pdp_osm_20260119_150045.png",
        "matched_selector": null,
        "matched_text": "Klarna, Del op"
      },
      "timestamp": "2026-01-19T15:00:45Z"
    },
    {
      "check_id": "CART_KLARNA",
      "status": "PASS",
      "evidence": {
        "screenshot_path": "out/humac.dk/cart_20260119_150100.png",
        "matched_selector": null,
        "matched_text": "Klarna"
      },
      "timestamp": "2026-01-19T15:01:00Z"
    },
    {
      "check_id": "CHECKOUT_PAYMENT_POSITION",
      "status": "PASS",
      "evidence": {
        "screenshot_path": "out/humac.dk/checkout_payment_20260119_150115.png",
        "matched_selector": null,
        "matched_text": "Payment method at position 2"
      },
      "timestamp": "2026-01-19T15:01:15Z",
      "payment_methods": [
        "Credit Card",
        "Klarna",
        "PayPal"
      ],
      "klarna_index": 2
    }
  ],
  "summary": {
    "total": 4,
    "passed": 4,
    "failed": 0
  }
}
```

## 7. Key Implementation Details

### 7.1 Timeouts
- Navigation timeout: 30s
- Element wait timeout: 10s
- Network idle wait: 10s (for page ready)

### 7.2 Error Isolation
- Each check is wrapped in try-except
- Check failures don't block other checks
- All errors are recorded in report with error messages

### 8. CLI Usage

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run audit
python -m auditor.run --out-dir out --headless true

# Run with visible browser (for debugging)
python -m auditor.run --out-dir out --headless false
```

## 9. Deliverables Checklist

- [x] Directory structure
- [x] Function signatures for all modules
- [x] Execution flow pseudo-code
- [ ] Implementation code (to be done after confirmation)
- [ ] README with installation and usage
- [ ] Integration tests

---

**Please confirm this design before implementation.**
