# Phase 0 Implementation Design

## 1. Project Directory Structure

```
klarna-integration-auto-auditor/
├── app/
│   ├── __init__.py
│   ├── run.py                    # CLI entry point (existing, will extend)
│   ├── phase0/
│   │   ├── __init__.py
│   │   ├── auditor.py            # Phase 0 main auditor
│   │   ├── workflow.py           # Workflow orchestrator
│   │   └── config.py             # Configuration loader
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auditor.py            # (existing)
│   │   ├── browser.py            # (existing, will extend)
│   │   └── rule_engine.py        # (existing)
│   ├── detectors/
│   │   ├── __init__.py
│   │   ├── footer_klarna_logo_detector.py  # (existing, will extend)
│   │   ├── pdp_osm_detector.py   # NEW: PDP OSM detector
│   │   ├── cart_klarna_detector.py  # NEW: Cart Klarna detector
│   │   └── checkout_payment_detector.py  # NEW: Checkout payment position detector
│   ├── data/
│   │   ├── __init__.py
│   │   └── merchant_loader.py    # (existing)
│   ├── report/
│   │   ├── __init__.py
│   │   ├── report_generator.py   # (existing, will extend)
│   │   └── screenshot_manager.py # NEW: Screenshot manager
│   └── utils/
│       ├── __init__.py
│       ├── logger.py             # NEW: Enhanced logging
│       └── validators.py          # (existing)
├── configs/
│   ├── phase0_config.yaml         # NEW: Phase 0 configuration
│   └── test_addresses.json       # NEW: Test addresses for checkout (multi-country)
├── data/
│   ├── merchant_registry.csv     # (existing)
│   └── addresses/
│       └── addresses.json        # NEW: Manual address input interface
├── tests/
│   ├── phase0/
│   │   ├── __init__.py
│   │   ├── test_phase0_auditor.py
│   │   ├── test_workflow.py
│   │   └── fixtures/
│   │       ├── good_case_humac.html  # Fixture for good case
│   │       └── bad_case_no_klarna.html  # Fixture for bad case
│   ├── test_footer_klarna_logo_detector.py  # (existing)
│   └── test_report_generator.py  # (existing)
├── data/
│   └── merchant_registry.csv     # (existing)
├── requirements.txt
├── README.md
└── DESIGN.md
```

## 2. Core Module Function Signatures

### 2.1 app/phase0/auditor.py - Phase 0 Main Auditor

```python
class Phase0Auditor:
    """Phase 0 auditor for single merchant audit"""
    
    def __init__(
        self,
        base_url: str,
        pdp_url: str,
        config: Phase0Config,
        browser_manager: BrowserManager
    ) -> None:
        """
        Initialize Phase 0 auditor
        
        Args:
            base_url: Merchant base URL
            pdp_url: Sample product detail page URL
            config: Phase 0 configuration
            browser_manager: Browser manager instance
        """
        pass
    
    async def run_audit(self) -> Phase0AuditResult:
        """
        Run complete Phase 0 audit workflow
        
        Returns:
            Phase0AuditResult with all check results
        """
        pass
    
    async def check_footer_klarna_logo(self) -> CheckResult:
        """
        Check 1: FOOTER_KLARNA_LOGO
        - Navigate to base_url
        - Wait for page load
        - Capture footer screenshot
        - Detect Klarna logo in footer
        
        Returns:
            CheckResult with status, evidence, confidence
        """
        pass
    
    async def check_pdp_osm(self) -> CheckResult:
        """
        Check 2: PDP_OSM
        - Navigate to pdp_url
        - Wait for price and buy button
        - Capture OSM visible area screenshot
        - Detect Klarna OSM keywords
        
        Returns:
            CheckResult with status, evidence, confidence
        """
        pass
    
    async def check_cart_klarna(self) -> CheckResult:
        """
        Check 3: CART_KLARNA
        - Click add to cart on PDP
        - Navigate to /cart
        - Wait for page load
        - Capture cart area screenshot
        - Detect Klarna in cart (keyword/network)
        
        Returns:
            CheckResult with status, evidence, confidence
        """
        pass
    
    async def check_checkout_payment_position(self) -> CheckResult:
        """
        Check 4: CHECKOUT_PAYMENT_POSITION
        - Navigate from cart to checkout
        - Fill test address if needed
        - Wait for payment methods to load
        - Scan payment methods, find Klarna position
        - Capture payment methods area screenshot
        
        Returns:
            CheckResult with status, evidence, confidence (includes position index)
        """
        pass
```

### 2.2 app/phase0/workflow.py - Workflow Orchestrator

```python
class Phase0Workflow:
    """Orchestrates Phase 0 audit workflow"""
    
    def __init__(
        self,
        auditor: Phase0Auditor,
        screenshot_manager: ScreenshotManager
    ) -> None:
        """
        Initialize workflow
        
        Args:
            auditor: Phase 0 auditor instance
            screenshot_manager: Screenshot manager instance
        """
        pass
    
    async def execute(self) -> Phase0AuditResult:
        """
        Execute complete workflow with error isolation
        
        Returns:
            Phase0AuditResult with all check results
        """
        pass
    
    async def _execute_check_with_isolation(
        self,
        check_name: str,
        check_func: Callable
    ) -> CheckResult:
        """
        Execute a single check with error isolation
        
        Args:
            check_name: Name of the check
            check_func: Async function to execute
            
        Returns:
            CheckResult (even if check fails)
        """
        pass
```

### 2.3 app/phase0/config.py - Configuration Loader

```python
@dataclass
class Phase0Config:
    """Phase 0 configuration"""
    base_url: str
    pdp_url: str
    output_dir: str
    headless: bool = True
    viewport: str = "desktop"  # "desktop" | "mobile"
    test_address: Optional[Dict[str, str]] = None
    test_address_country: Optional[str] = None  # Country code (e.g., "SE", "DK")
    timeouts: Dict[str, int] = None  # navigation, element_wait, network_idle
    retries: int = 2
    enable_har: bool = False

class Phase0ConfigLoader:
    """Load Phase 0 configuration from CLI args or YAML"""
    
    @staticmethod
    def from_cli_args(args: argparse.Namespace) -> Phase0Config:
        """Load config from command line arguments"""
        pass
    
    @staticmethod
    def from_yaml(yaml_path: str) -> Phase0Config:
        """Load config from YAML file"""
        pass
```

### 2.3.1 app/data/address_manager.py - Address Manager

```python
@dataclass
class TestAddress:
    """Test address data model"""
    first_name: str
    last_name: str
    email: str
    phone: str
    street: str
    postal_code: str
    city: str
    country: str  # ISO country code (e.g., "SE", "DK", "NO")
    region: Optional[str] = None  # State/Province/Region

class AddressManager:
    """Manage test addresses for different countries"""
    
    def __init__(self, addresses_file: str = "data/addresses/addresses.json"):
        """
        Initialize address manager
        
        Args:
            addresses_file: Path to addresses JSON file
        """
        self.addresses_file = Path(addresses_file)
        self.addresses: Dict[str, TestAddress] = {}
        self.load()
    
    def load(self) -> None:
        """Load addresses from JSON file"""
        if not self.addresses_file.exists():
            # Create default structure if file doesn't exist
            self._create_default_file()
            return
        
        with open(self.addresses_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for country_code, addr_data in data.items():
                self.addresses[country_code] = TestAddress(**addr_data)
    
    def save(self) -> None:
        """Save addresses to JSON file"""
        self.addresses_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            country: {
                "first_name": addr.first_name,
                "last_name": addr.last_name,
                "email": addr.email,
                "phone": addr.phone,
                "street": addr.street,
                "postal_code": addr.postal_code,
                "city": addr.city,
                "country": addr.country,
                "region": addr.region
            }
            for country, addr in self.addresses.items()
        }
        with open(self.addresses_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_address(self, country_code: str) -> Optional[TestAddress]:
        """
        Get address for a country
        
        Args:
            country_code: ISO country code (e.g., "SE", "DK")
            
        Returns:
            TestAddress or None if not found
        """
        return self.addresses.get(country_code.upper())
    
    def add_address(self, address: TestAddress) -> None:
        """
        Add or update address for a country
        
        Args:
            address: TestAddress object
        """
        self.addresses[address.country.upper()] = address
        self.save()
    
    def remove_address(self, country_code: str) -> bool:
        """
        Remove address for a country
        
        Args:
            country_code: ISO country code
            
        Returns:
            True if removed, False if not found
        """
        if country_code.upper() in self.addresses:
            del self.addresses[country_code.upper()]
            self.save()
            return True
        return False
    
    def list_countries(self) -> List[str]:
        """Get list of available country codes"""
        return sorted(self.addresses.keys())
    
    def _create_default_file(self) -> None:
        """Create default addresses file with example"""
        default_addresses = {
            "SE": {
                "first_name": "Test",
                "last_name": "User",
                "email": "test+klarna@example.com",
                "phone": "+46123456789",
                "street": "Testgatan 1",
                "postal_code": "11122",
                "region": "Stockholm",
                "city": "Stockholm",
                "country": "SE"
            }
        }
        self.addresses_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.addresses_file, 'w', encoding='utf-8') as f:
            json.dump(default_addresses, f, indent=2, ensure_ascii=False)
        self.load()
```

### 2.4 app/detectors/pdp_osm_detector.py - PDP OSM Detector

```python
class PDPOSMDetector:
    """Detect Klarna On-Site Messaging on PDP"""
    
    KEYWORDS = ["Klarna", "Del op", "Kort", "Klarna Pay", "Klarna logo"]
    
    async def detect(
        self,
        page: Page,
        browser_manager: BrowserManager
    ) -> DetectionResult:
        """
        Detect OSM in PDP content area or near price
        
        Args:
            page: Playwright page object
            browser_manager: Browser manager instance
            
        Returns:
            DetectionResult with matched keywords and locations
        """
        pass
    
    async def wait_for_pdp_ready(
        self,
        page: Page,
        timeout: int = 10000
    ) -> bool:
        """
        Wait for PDP to be ready (price and buy button visible)
        
        Args:
            page: Playwright page object
            timeout: Timeout in milliseconds
            
        Returns:
            True if ready, False if timeout
        """
        pass
```

### 2.5 app/detectors/cart_klarna_detector.py - Cart Klarna Detector

```python
class CartKlarnaDetector:
    """Detect Klarna in cart page"""
    
    async def detect(
        self,
        page: Page,
        browser_manager: BrowserManager,
        network_requests: Optional[List[NetworkRequest]] = None
    ) -> DetectionResult:
        """
        Detect Klarna in cart (keyword or network)
        
        Args:
            page: Playwright page object
            browser_manager: Browser manager instance
            network_requests: Optional list of network requests
            
        Returns:
            DetectionResult with detection method and evidence
        """
        pass
    
    async def detect_keyword(self, page: Page) -> DetectionResult:
        """Detect Klarna keyword in cart content"""
        pass
    
    async def detect_network(
        self,
        network_requests: List[NetworkRequest]
    ) -> DetectionResult:
        """Detect Klarna in network requests"""
        pass
```

### 2.6 app/detectors/checkout_payment_detector.py - Checkout Payment Detector

```python
class CheckoutPaymentDetector:
    """Detect Klarna payment method position in checkout"""
    
    PAYMENT_SELECTORS = [
        'input[name="payment_method"]',
        '.payment-options',
        '.payment-methods',
        '[data-payment-method]',
        '.payment-method',
        'label[for*="payment"]',
        '.payment-option',
        '[class*="payment"]'
    ]
    
    async def detect(
        self,
        page: Page,
        browser_manager: BrowserManager,
        max_wait: int = 10000
    ) -> DetectionResult:
        """
        Find Klarna in payment methods list and return position
        
        Strategy:
        1. Wait for networkidle
        2. Try multiple payment selectors
        3. Collect all visible labels/texts into array
        4. Case-insensitive contains("klarna") match
        5. Return index (1-based)
        
        Args:
            page: Playwright page object
            browser_manager: Browser manager instance
            max_wait: Maximum wait time for payment methods to load
            
        Returns:
            DetectionResult with position index (1-based) or None
        """
        pass
    
    async def wait_for_payment_methods(
        self,
        page: Page,
        browser_manager: BrowserManager,
        timeout: int = 10000
    ) -> bool:
        """
        Wait for payment methods to be visible
        Strategy: networkidle + wait_for_selector (multiple fallbacks)
        """
        pass
    
    async def find_payment_methods_list(
        self,
        page: Page,
        browser_manager: BrowserManager
    ) -> List[WebElement]:
        """
        Find payment methods list element
        Check main frame and all iframes if not found
        """
        pass
    
    async def collect_payment_method_labels(
        self,
        payment_elements: List[WebElement]
    ) -> List[str]:
        """
        Collect all visible labels/texts from payment method elements
        
        Args:
            payment_elements: List of payment method elements
            
        Returns:
            List of visible text labels
        """
        pass
    
    async def get_klarna_position(
        self,
        payment_labels: List[str]
    ) -> Optional[int]:
        """
        Get Klarna position in payment methods list (1-based)
        Case-insensitive contains("klarna") match
        
        Args:
            payment_labels: List of payment method labels
            
        Returns:
            Position index (1-based) or None if not found
        """
        pass
```

### 2.7 app/core/browser.py - Extended Browser Manager

```python
class BrowserManager:
    """Extended browser manager for Phase 0"""
    
    # Existing methods...
    
    async def wait_for_load_state_and_selector(
        self,
        selectors: List[str],
        fallback_keywords: List[str] = None,
        timeout: int = 10000
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Wait strategy: networkidle + wait_for_selector (multiple fallbacks) + keyword fallback
        
        Args:
            selectors: List of selectors to try (in order)
            fallback_keywords: Optional keywords to search in page text if selectors fail
            timeout: Timeout in milliseconds
            
        Returns:
            Tuple of (success, matched_selector, matched_keyword)
        """
        pass
    
    async def wait_for_price_and_buy_button(
        self,
        price_selectors: List[str] = None,
        buy_button_selectors: List[str] = None,
        fallback_keywords: List[str] = None,
        timeout: int = 10000
    ) -> bool:
        """
        Wait for price and buy button with multiple selector fallbacks
        
        Args:
            price_selectors: List of price selectors to try
            buy_button_selectors: List of buy button selectors to try
            fallback_keywords: Keywords to search if selectors fail
            timeout: Timeout in milliseconds
            
        Returns:
            True if both found, False if timeout
        """
        pass
    
    async def find_element_in_frames(
        self,
        selector: str,
        check_all_frames: bool = True
    ) -> Tuple[Optional[WebElement], Optional[Frame]]:
        """
        Find element, checking iframe frames if not found in main frame
        
        Args:
            selector: CSS selector to find
            check_all_frames: If True, check all frames if not found in main
            
        Returns:
            Tuple of (element, frame) or (None, None) if not found
        """
        pass
    
    async def get_element_snippet_and_path(
        self,
        element: WebElement
    ) -> Dict[str, str]:
        """
        Get DOM snippet (innerHTML) and selector path (xpath/CSS path)
        
        Args:
            element: WebElement to analyze
            
        Returns:
            Dictionary with 'snippet' and 'path' (xpath or CSS selector)
        """
        pass
    
    async def click_add_to_cart(
        self,
        selectors: List[str] = None
    ) -> bool:
        """
        Click add to cart button with multiple selector fallbacks
        
        Args:
            selectors: List of selectors to try (default common selectors)
            
        Returns:
            True if clicked, False if not found
        """
        pass
    
    async def fill_test_address(
        self,
        address: TestAddress
    ) -> bool:
        """
        Fill test address in checkout form
        
        Args:
            address: TestAddress object with address fields
            
        Returns:
            True if filled successfully
        """
        pass
    
    async def detect_address_form_fields(
        self,
        page: Page
    ) -> Dict[str, str]:
        """
        Detect address form field selectors on checkout page
        
        Returns:
            Dictionary mapping field names to selectors
        """
        pass
    
    async def capture_network_har(
        self,
        output_path: str
    ) -> bool:
        """
        Capture network HAR file
        
        Args:
            output_path: Path to save HAR file
            
        Returns:
            True if saved successfully
        """
        pass
    
    async def get_network_requests(
        self,
        filter_pattern: str = None
    ) -> List[NetworkRequest]:
        """
        Get network requests (optionally filtered)
        
        Args:
            filter_pattern: Optional regex pattern to filter URLs
            
        Returns:
            List of network requests
        """
        pass
    
    async def detect_klarna_in_network(
        self,
        har_data: Dict = None
    ) -> Tuple[bool, List[Dict[str, str]]]:
        """
        Detect Klarna in network requests (HAR or live)
        Check if any request domain or path contains "klarna"
        Examples: cdn.klarna.com, klarna.*
        
        Args:
            har_data: Optional HAR data dict (if None, uses live network)
            
        Returns:
            Tuple of (found, list of matching requests with url/domain)
        """
        pass
```

### 2.8 app/report/screenshot_manager.py - Screenshot Manager

```python
class ScreenshotManager:
    """Manage screenshots for Phase 0 audit"""
    
    def __init__(self, base_dir: str, merchant: str) -> None:
        """
        Initialize screenshot manager
        
        Args:
            base_dir: Base output directory
            merchant: Merchant identifier (e.g., "humac.dk")
        """
        self.base_dir = Path(base_dir)
        self.merchant = merchant
        self.merchant_dir = self.base_dir / merchant
        self.merchant_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_path(self, page_type: str) -> str:
        """
        Generate screenshot path: {out_dir}/{merchant}/{page_type}_{yyyyMMdd_HHmmss}.png
        
        Args:
            page_type: Type of page (footer, pdp_osm, cart, checkout_payment)
            
        Returns:
            Full path to screenshot file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{page_type}_{timestamp}.png"
        return str(self.merchant_dir / filename)
    
    def get_footer_path(self) -> str:
        """Get path for footer screenshot"""
        return self._generate_path("footer")
    
    def get_pdp_osm_path(self) -> str:
        """Get path for PDP OSM screenshot"""
        return self._generate_path("pdp_osm")
    
    def get_cart_path(self) -> str:
        """Get path for cart screenshot"""
        return self._generate_path("cart")
    
    def get_checkout_payment_path(self) -> str:
        """Get path for checkout payment methods screenshot"""
        return self._generate_path("checkout_payment")
    
    async def capture_footer(
        self,
        browser_manager: BrowserManager
    ) -> str:
        """Capture footer screenshot and return path"""
        path = self.get_footer_path()
        await browser_manager.capture_screenshot(path)
        return path
    
    async def capture_pdp_osm(
        self,
        browser_manager: BrowserManager
    ) -> str:
        """Capture PDP OSM area screenshot and return path"""
        path = self.get_pdp_osm_path()
        await browser_manager.capture_screenshot(path)
        return path
    
    async def capture_cart(
        self,
        browser_manager: BrowserManager
    ) -> str:
        """Capture cart area screenshot and return path"""
        path = self.get_cart_path()
        await browser_manager.capture_screenshot(path)
        return path
    
    async def capture_checkout_payment(
        self,
        browser_manager: BrowserManager
    ) -> str:
        """Capture checkout payment methods screenshot and return path"""
        path = self.get_checkout_payment_path()
        await browser_manager.capture_screenshot(path)
        return path
```

### 2.9 app/report/report_generator.py - Extended Report Generator

```python
class Phase0ReportGenerator:
    """Generate Phase 0 JSON report"""
    
    def __init__(self, output_dir: str) -> None:
        """Initialize report generator"""
        pass
    
    def generate(
        self,
        result: Phase0AuditResult,
        filename: str = None
    ) -> str:
        """
        Generate Phase 0 JSON report
        
        Args:
            result: Phase0AuditResult object
            filename: Optional filename
            
        Returns:
            Path to generated report file
        """
        pass
    
    def _format_check_result(
        self,
        check: CheckResult
    ) -> Dict[str, Any]:
        """Format single check result to JSON schema"""
        pass
```

### 2.10 Data Models

```python
@dataclass
class CheckResult:
    """Result of a single check"""
    check_id: str
    status: str  # "PASS" | "FAIL" | "WARN"
    confidence: str  # "high" | "medium" | "low"
    evidence: Evidence
    timestamp: str
    error: Optional[str] = None
    position: Optional[int] = None  # For CHECKOUT_PAYMENT_POSITION

@dataclass
class Evidence:
    """Evidence for a check result"""
    screenshot: Optional[str] = None
    matched_selector: Optional[str] = None  # CSS selector or xpath
    selector_path: Optional[str] = None  # Full path (xpath or CSS path)
    snippet: Optional[str] = None  # element.innerHTML
    matched_keywords: List[str] = None
    network_requests: List[Dict] = None  # For network detection
    matched_dom: Optional[str] = None  # Full DOM snippet

@dataclass
class Phase0AuditResult:
    """Complete Phase 0 audit result"""
    merchant: str
    run_id: str
    results: List[CheckResult]
    summary: Dict[str, int]  # passed, failed, warned
    timestamp: str
```

## 3. Pseudo-code Workflow

### 3.1 Main Execution Flow

```python
async def main():
    # 1. Parse CLI arguments
    args = parse_arguments()
    
    # 2. Load configuration
    config = Phase0ConfigLoader.from_cli_args(args)
    
    # 3. Initialize components
    browser = BrowserManager(config)
    screenshot_manager = ScreenshotManager(config.output_dir, extract_merchant(config.base_url))
    auditor = Phase0Auditor(config.base_url, config.pdp_url, config, browser)
    workflow = Phase0Workflow(auditor, screenshot_manager)
    
    # 4. Start browser
    await browser.start()
    
    try:
        # 5. Execute workflow
        result = await workflow.execute()
        
        # 6. Generate report
        report_generator = Phase0ReportGenerator(config.output_dir)
        report_path = report_generator.generate(result)
        
        # 7. Print summary
        print_summary(result)
        
    finally:
        # 8. Cleanup
        await browser.close()
```

### 3.2 Workflow Execution Flow

```python
async def execute():
    results = []
    
    # Check 1: FOOTER_KLARNA_LOGO
    result1 = await _execute_check_with_isolation(
        "FOOTER_KLARNA_LOGO",
        auditor.check_footer_klarna_logo
    )
    results.append(result1)
    
    # Check 2: PDP_OSM
    result2 = await _execute_check_with_isolation(
        "PDP_OSM",
        auditor.check_pdp_osm
    )
    results.append(result2)
    
    # Check 3: CART_KLARNA
    result3 = await _execute_check_with_isolation(
        "CART_KLARNA",
        auditor.check_cart_klarna
    )
    results.append(result3)
    
    # Check 4: CHECKOUT_PAYMENT_POSITION
    result4 = await _execute_check_with_isolation(
        "CHECKOUT_PAYMENT_POSITION",
        auditor.check_checkout_payment_position
    )
    results.append(result4)
    
    # Create summary
    summary = calculate_summary(results)
    
    return Phase0AuditResult(
        merchant=extract_merchant(config.base_url),
        run_id=generate_run_id(),
        results=results,
        summary=summary,
        timestamp=datetime.now().isoformat() + "Z"
    )
```

### 3.3 Individual Check Flow (FOOTER_KLARNA_LOGO)

```python
async def check_footer_klarna_logo():
    try:
        # 1. Navigate to base_url
        success = await browser.navigate(base_url)
        if not success:
            return CheckResult(status="FAIL", error="Navigation failed")
        
        # 2. Wait for page load
        await browser.wait_for_load_state("networkidle")
        
        # 3. Capture footer screenshot
        screenshot_path = await screenshot_manager.capture_footer(browser)
        
        # 4. Detect Klarna logo (check main frame and iframes)
        detector = FooterKlarnaLogoDetector()
        
        # Try main frame first
        detection = await detector.detect(
            await browser.get_page_source(),
            browser
        )
        
        # If not found, check iframes
        if not detection.passed:
            element, frame = await browser.find_element_in_frames('footer img[src*="klarna"], footer img[alt*="klarna"]')
            if element:
                element_info = await browser.get_element_snippet_and_path(element)
                detection.matched_element = element
                detection.matched_selectors = [element_info.get('path')]
                detection.passed = True
                detection.confidence = 0.95
        
        # 5. Build evidence with DOM snippet and selector path
        matched_element = detection.matched_element if hasattr(detection, 'matched_element') else None
        evidence_data = {}
        
        if matched_element:
            # Get element snippet and path
            element_info = await browser.get_element_snippet_and_path(matched_element)
            evidence_data = {
                "screenshot": screenshot_path,
                "matched_selector": detection.matched_selectors[0] if detection.matched_selectors else None,
                "selector_path": element_info.get('path'),
                "snippet": element_info.get('snippet'),
                "matched_dom": element_info.get('snippet')
            }
        else:
            evidence_data = {
                "screenshot": screenshot_path,
                "matched_selector": detection.matched_selectors[0] if detection.matched_selectors else None,
                "snippet": None
            }
        
        evidence = Evidence(**evidence_data)
        
        # 6. Determine status and confidence
        status = "PASS" if detection.passed else "FAIL"
        confidence = map_confidence(detection.confidence)
        
        return CheckResult(
            check_id="FOOTER_KLARNA_LOGO",
            status=status,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.now().isoformat() + "Z"
        )
        
    except Exception as e:
        return CheckResult(
            check_id="FOOTER_KLARNA_LOGO",
            status="FAIL",
            confidence="low",
            evidence=Evidence(),
            timestamp=datetime.now().isoformat() + "Z",
            error=str(e)
        )
```

### 3.4 Individual Check Flow (PDP_OSM)

```python
async def check_pdp_osm():
    try:
        # 1. Navigate to pdp_url
        success = await browser.navigate(pdp_url)
        if not success:
            return CheckResult(status="FAIL", error="Navigation failed")
        
        # 2. Wait for price and buy button with fallback strategy
        detector = PDPOSMDetector()
        
        # Wait strategy: networkidle + multiple selectors + keyword fallback
        price_selectors = ['.price', '[class*="price"]', '[data-price]', '#price']
        buy_button_selectors = ['button[class*="buy"]', 'button[class*="cart"]', 'button[class*="add"]', '[data-add-to-cart]']
        fallback_keywords = ['price', 'buy', 'add to cart']
        
        ready, matched_selector, matched_keyword = await browser.wait_for_load_state_and_selector(
            selectors=price_selectors + buy_button_selectors,
            fallback_keywords=fallback_keywords,
            timeout=10000
        )
        
        if not ready:
            return CheckResult(status="WARN", error="PDP not ready (price/buy button not found)")
        
        # 3. Capture OSM area screenshot
        screenshot_path = await screenshot_manager.capture_pdp_osm(browser)
        
        # 4. Detect OSM keywords (check main frame and all iframes)
        detection = await detector.detect(browser.page, browser)
        
        # If not found in main frame, check iframes
        if not detection.passed:
            element, frame = await browser.find_element_in_frames('[class*="klarna"], [id*="klarna"]')
            if element:
                element_info = await browser.get_element_snippet_and_path(element)
                detection.matched_element = element
                detection.matched_selectors = [element_info.get('path')]
                detection.passed = True
        
        # 5. Build evidence
        evidence = Evidence(
            screenshot=screenshot_path,
            matched_keywords=detection.matched_keywords
        )
        
        status = "PASS" if detection.passed else "FAIL"
        confidence = map_confidence(detection.confidence)
        
        return CheckResult(
            check_id="PDP_OSM",
            status=status,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.now().isoformat() + "Z"
        )
        
    except Exception as e:
        return CheckResult(
            check_id="PDP_OSM",
            status="FAIL",
            confidence="low",
            evidence=Evidence(),
            timestamp=datetime.now().isoformat() + "Z",
            error=str(e)
        )
```

### 3.5 Individual Check Flow (CART_KLARNA)

```python
async def check_cart_klarna():
    try:
        # 1. Click add to cart (assumes we're on PDP)
        success = await browser.click_add_to_cart()
        if not success:
            return CheckResult(status="FAIL", error="Add to cart button not found")
        
        # 2. Navigate to /cart
        cart_url = urljoin(base_url, "/cart")
        success = await browser.navigate(cart_url)
        if not success:
            return CheckResult(status="FAIL", error="Cart navigation failed")
        
        # 3. Wait for cart to load
        await browser.wait_for_load_state("networkidle")
        
        # 4. Capture cart screenshot
        screenshot_path = await screenshot_manager.capture_cart(browser)
        
        # 5. Detect Klarna (keyword or network)
        detector = CartKlarnaDetector()
        
        # Capture HAR for network detection
        har_path = None
        if config.enable_har:
            har_path = screenshot_manager.merchant_dir / f"cart_network_{datetime.now().strftime('%Y%m%d_%H%M%S')}.har"
            await browser.capture_network_har(str(har_path))
        
        # Detect in network (HAR or live)
        network_found, network_matches = await browser.detect_klarna_in_network()
        
        # Also try keyword detection
        keyword_detection = await detector.detect_keyword(browser.page)
        
        # 6. Build evidence
        evidence = Evidence(
            screenshot=screenshot_path,
            matched_keywords=keyword_detection.matched_keywords if keyword_detection.passed else None,
            network_requests=network_matches if network_found else None
        )
        
        status = "PASS" if detection.passed else "FAIL"
        confidence = map_confidence(detection.confidence)
        
        return CheckResult(
            check_id="CART_KLARNA",
            status=status,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.now().isoformat() + "Z"
        )
        
    except Exception as e:
        return CheckResult(
            check_id="CART_KLARNA",
            status="FAIL",
            confidence="low",
            evidence=Evidence(),
            timestamp=datetime.now().isoformat() + "Z",
            error=str(e)
        )
```

### 3.6 Individual Check Flow (CHECKOUT_PAYMENT_POSITION)

```python
async def check_checkout_payment_position():
    try:
        # 1. Navigate to checkout (assumes we're on cart)
        checkout_url = urljoin(base_url, "/checkout")
        success = await browser.navigate(checkout_url)
        if not success:
            return CheckResult(status="FAIL", error="Checkout navigation failed")
        
        # 2. Fill test address if needed
        if needs_address_fill(browser.page):
            # Get address from address manager based on country
            address_manager = AddressManager()
            country_code = config.test_address_country or detect_country_from_url(base_url)
            address = address_manager.get_address(country_code)
            
            if not address:
                return CheckResult(status="WARN", error=f"No test address found for country: {country_code}")
            
            success = await browser.fill_test_address(address)
            if not success:
                return CheckResult(status="WARN", error="Address fill failed")
        
        # 3. Wait for payment methods to load
        detector = CheckoutPaymentDetector()
        
        # Wait strategy: networkidle + multiple selectors
        await browser.page.wait_for_load_state("networkidle", timeout=10000)
        ready = await detector.wait_for_payment_methods(browser.page, browser, timeout=10000)
        
        if not ready:
            return CheckResult(status="WARN", error="Payment methods not loaded")
        
        # 4. Find payment methods list (check main frame and iframes)
        payment_methods = await detector.find_payment_methods_list(browser.page, browser)
        if not payment_methods:
            return CheckResult(status="FAIL", error="Payment methods list not found")
        
        # 5. Collect all visible payment method labels
        payment_labels = await detector.collect_payment_method_labels(payment_methods)
        
        # 6. Get Klarna position (case-insensitive contains match)
        position = await detector.get_klarna_position(payment_labels)
        
        # 7. Get element snippet and path if found
        element_info = {}
        if position and payment_methods:
            klarna_element = payment_methods[position - 1]  # Convert to 0-based
            element_info = await browser.get_element_snippet_and_path(klarna_element)
        
        # 8. Capture payment methods screenshot
        screenshot_path = await screenshot_manager.capture_checkout_payment(browser)
        
        # 9. Build evidence
        evidence = Evidence(
            screenshot=screenshot_path,
            matched_selector=f"payment_methods[{position}]" if position else None,
            selector_path=element_info.get('path') if element_info else None,
            snippet=element_info.get('snippet') if element_info else None,
            matched_dom=element_info.get('snippet') if element_info else None
        )
        
        status = "PASS" if position else "FAIL"
        confidence = "high" if position else "low"
        
        return CheckResult(
            check_id="CHECKOUT_PAYMENT_POSITION",
            status=status,
            confidence=confidence,
            evidence=evidence,
            timestamp=datetime.now().isoformat() + "Z",
            position=position
        )
        
    except Exception as e:
        return CheckResult(
            check_id="CHECKOUT_PAYMENT_POSITION",
            status="FAIL",
            confidence="low",
            evidence=Evidence(),
            timestamp=datetime.now().isoformat() + "Z",
            error=str(e)
        )
```

## 4. CLI Interface

```python
# app/run.py extension
parser.add_argument('--phase0', action='store_true', help='Run Phase 0 audit')
parser.add_argument('--base-url', help='Merchant base URL')
parser.add_argument('--pdp-url', help='Sample product detail page URL')
parser.add_argument('--out-dir', default='out/', help='Output directory')
parser.add_argument('--headless', action='store_true', default=True, help='Run headless')
parser.add_argument('--viewport', choices=['desktop', 'mobile'], default='desktop')
parser.add_argument('--test-address-json', help='Path to test address JSON file (default: data/addresses/addresses.json)')
parser.add_argument('--test-address-country', help='Country code for test address (e.g., SE, DK, NO). Auto-detected from URL if not provided')
parser.add_argument('--config', help='Path to config YAML file')
```

## 5. Configuration Files

### 5.1 configs/phase0_config.yaml

```yaml
phase0:
  timeouts:
    navigation: 30000
    element_wait: 10000
    network_idle: 10000
  retries: 2
  enable_har: false
  viewport: "desktop"  # or "mobile"
  test_address_country: "SE"  # Optional: override country code
```

### 5.2 data/addresses/addresses.json - Manual Address Input

```json
{
  "SE": {
    "first_name": "Test",
    "last_name": "User",
    "email": "test+klarna@example.com",
    "phone": "+46123456789",
    "street": "Testgatan 1",
    "postal_code": "11122",
    "region": "Stockholm",
    "city": "Stockholm",
    "country": "SE"
  },
  "DK": {
    "first_name": "Test",
    "last_name": "User",
    "email": "test+klarna@example.com",
    "phone": "+4512345678",
    "street": "Testgade 1",
    "postal_code": "2100",
    "region": "Copenhagen",
    "city": "Copenhagen",
    "country": "DK"
  },
  "NO": {
    "first_name": "Test",
    "last_name": "User",
    "email": "test+klarna@example.com",
    "phone": "+4712345678",
    "street": "Testgate 1",
    "postal_code": "0150",
    "region": "Oslo",
    "city": "Oslo",
    "country": "NO"
  }
}
```

**Note**: This file can be manually edited to add/update addresses for different countries. The AddressManager will automatically load and save changes.

## 6. Test Strategy

### 6.1 Integration Test - Good Case (humac.dk)

```python
@pytest.mark.asyncio
async def test_phase0_good_case_humac():
    """Test Phase 0 with real humac.dk website"""
    config = Phase0Config(
        base_url="https://www.humac.dk/",
        pdp_url="https://www.humac.dk/produkter/headphones/airpods-pro-3",
        output_dir="out/test_humac",
        headless=True
    )
    
    browser = BrowserManager(config)
    auditor = Phase0Auditor(config.base_url, config.pdp_url, config, browser)
    
    await browser.start()
    try:
        result = await auditor.run_audit()
        
        # Assertions
        assert result.summary["passed"] >= 2  # At least 2 checks should pass
        assert any(r.check_id == "FOOTER_KLARNA_LOGO" and r.status == "PASS" 
                  for r in result.results)
    finally:
        await browser.close()
```

### 6.2 Integration Test - Bad Case (Static HTML Fixture)

```python
@pytest.mark.asyncio
async def test_phase0_bad_case_no_klarna():
    """Test Phase 0 with static HTML fixture without Klarna"""
    # Serve static HTML fixture
    fixture_path = "tests/phase0/fixtures/bad_case_no_klarna.html"
    
    # Run audit against fixture
    # Assert all checks fail
    pass
```

## 7. Address Management Interface

### 7.1 Manual Address Input

Users can manually edit `data/addresses/addresses.json` to add/update addresses for different countries. The file structure:

```json
{
  "COUNTRY_CODE": {
    "first_name": "...",
    "last_name": "...",
    "email": "...",
    "phone": "...",
    "street": "...",
    "postal_code": "...",
    "region": "...",  // Optional
    "city": "...",
    "country": "COUNTRY_CODE"
  }
}
```

### 7.2 Address Manager CLI (Optional Future Enhancement)

```python
# Future: CLI tool to manage addresses
python -m app.address_manager add --country SE --first-name Test ...
python -m app.address_manager list
python -m app.address_manager remove --country SE
python -m app.address_manager show --country SE
```

### 7.3 Auto-detection

If `--test-address-country` is not provided, the system will:
1. Try to detect country from base_url (e.g., .dk → DK, .se → SE)
2. Fall back to default country or prompt user

## 8. Implementation Phases

### Phase 1: Core Infrastructure
- Extend BrowserManager with new methods
- Implement ScreenshotManager
- Create Phase0Config and loader
- Create AddressManager
- Create data models (CheckResult, Evidence, TestAddress, etc.)

### Phase 2: Detectors
- Extend FooterKlarnaLogoDetector
- Implement PDPOSMDetector
- Implement CartKlarnaDetector
- Implement CheckoutPaymentDetector

### Phase 3: Workflow
- Implement Phase0Auditor
- Implement Phase0Workflow
- Implement error isolation

### Phase 4: Reporting
- Extend ReportGenerator for Phase 0 schema
- Implement report formatting

### Phase 5: CLI & Testing
- Extend CLI interface
- Create integration tests
- Create fixtures

## 9. Notes

- All async operations should have proper timeout handling
- Network requests should be captured if enable_har is True
- Screenshots should be saved with format: `{out_dir}/{merchant}/{page_type}_{yyyyMMdd_HHmmss}.png`
- Error isolation: each check failure should not stop other checks
- Logging should be comprehensive (stdout + file)
- Viewport support: mobile vs desktop should change browser viewport size

## 10. Implementation Details

### 10.1 Waiting Strategy

All page interactions use a three-tier waiting strategy:

1. **Network Idle**: `page.wait_for_load_state("networkidle")` - Wait for network to be idle
2. **Selector Wait**: `page.wait_for_selector()` with multiple fallback selectors
3. **Keyword Fallback**: If selectors fail, search page text for keywords

Example:
```python
# Wait for price element
await page.wait_for_load_state("networkidle")
for selector in ['.price', '[class*="price"]', '[data-price]']:
    try:
        await page.wait_for_selector(selector, timeout=5000)
        break
    except:
        continue
else:
    # Fallback: search for "price" keyword in page text
    if "price" in (await page.text_content()).lower():
        # Found via keyword
        pass
```

### 10.2 Iframe Handling

If selector is not found in main frame, traverse all frames:

```python
# Try main frame first
element = await page.query_selector(selector)
if element:
    return element, page.main_frame

# Check all frames
for frame in page.frames:
    if frame != page.main_frame:
        element = await frame.query_selector(selector)
        if element:
            return element, frame

return None, None
```

### 10.3 Network Detection

Capture HAR and check for Klarna domains/paths:

```python
# Capture HAR
har = await page.context.tracing.stop()

# Parse HAR and check entries
for entry in har['log']['entries']:
    url = entry['request']['url']
    if 'klarna' in url.lower() or 'cdn.klarna.com' in url:
        # Found Klarna request
        matches.append({
            'url': url,
            'domain': extract_domain(url),
            'method': entry['request']['method']
        })
```

### 10.4 Payment Method Position Detection

Collect all visible labels/texts and do case-insensitive match:

```python
# Collect all payment method labels
labels = []
for element in payment_elements:
    text = await element.inner_text()
    if text.strip():
        labels.append(text.strip())

# Case-insensitive contains match
for i, label in enumerate(labels, start=1):
    if 'klarna' in label.lower():
        return i  # Return 1-based index

return None
```

### 10.5 Evidence Collection

For each matched element, collect:
- **DOM Snippet**: `element.innerHTML` or `element.outerHTML`
- **Selector Path**: Use `page.evaluate()` to get xpath or CSS path

```python
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

# Get snippet
snippet = await element.innerHTML()
```
