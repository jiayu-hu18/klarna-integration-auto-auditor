# Klarna Integration Auto Auditor - Project Design Document

## 1. Directory Structure

```
klarna-integration-auto-auditor/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Main program entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auditor.py             # Core audit engine
│   │   ├── browser.py             # Browser control (Selenium/Playwright)
│   │   └── rule_engine.py         # Rule engine
│   ├── detectors/
│   │   ├── __init__.py
│   │   ├── selector_detector.py   # CSS selector detector
│   │   ├── keyword_detector.py    # Keyword detector
│   │   └── network_detector.py    # Network request detector
│   ├── data/
│   │   ├── __init__.py
│   │   ├── merchant_loader.py     # Merchant data loader
│   │   └── rule_loader.py         # Rule configuration loader
│   ├── report/
│   │   ├── __init__.py
│   │   ├── report_generator.py    # Report generator
│   │   └── screenshot_manager.py  # Screenshot manager
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # Logging utility
│       └── validators.py          # Data validation utility
├── tests/
│   ├── __init__.py
│   ├── test_main.py
│   ├── test_core/
│   │   ├── __init__.py
│   │   ├── test_auditor.py
│   │   ├── test_browser.py
│   │   └── test_rule_engine.py
│   ├── test_detectors/
│   │   ├── __init__.py
│   │   ├── test_selector_detector.py
│   │   ├── test_keyword_detector.py
│   │   └── test_network_detector.py
│   └── test_data/
│       ├── __init__.py
│       ├── test_merchant_loader.py
│       └── test_rule_loader.py
├── configs/
│   ├── rules/
│   │   ├── checkout_rules.yaml    # Checkout page rules
│   │   ├── product_rules.yaml     # Product page rules
│   │   └── cart_rules.yaml        # Cart page rules
│   ├── browser_config.yaml        # Browser configuration
│   └── audit_config.yaml          # Main audit configuration
├── data/
│   └── merchant_registry.csv      # Merchant registry
├── reports/
│   └── .gitkeep                   # Report output directory
├── screenshots/
│   └── .gitkeep                   # Screenshot storage directory
├── requirements.txt
├── README.md
└── DESIGN.md                      # This document
```

## 2. Module Responsibilities and Key Function Signatures

### 2.1 core/auditor.py - Core Audit Engine

**Responsibility**: Coordinate the entire audit process, manage browser sessions, execute rule detection, generate reports

**Key Functions**:
```python
class Auditor:
    def __init__(self, config_path: str) -> None
    def load_merchants(self, csv_path: str) -> List[Merchant]
    def load_rules(self, rules_dir: str) -> List[Rule]
    def audit_merchant(self, merchant: Merchant) -> AuditResult
    def audit_all(self, merchants: List[Merchant]) -> List[AuditResult]
    def generate_report(self, results: List[AuditResult], output_path: str) -> str
```

### 2.2 core/browser.py - Browser Control

**Responsibility**: Manage browser instances, page navigation, network request interception, screenshots

**Key Functions**:
```python
class BrowserManager:
    def __init__(self, config: Dict[str, Any]) -> None
    def start(self) -> None
    def navigate(self, url: str, wait_time: int = 5) -> bool
    def get_page_source(self) -> str
    def find_elements(self, selector: str) -> List[WebElement]
    def capture_screenshot(self, file_path: str) -> bool
    def intercept_network_requests(self, callback: Callable) -> None
    def get_network_requests(self) -> List[NetworkRequest]
    def close(self) -> None
```

### 2.3 core/rule_engine.py - Rule Engine

**Responsibility**: Parse rule configurations, match rule types, execute detection logic

**Key Functions**:
```python
class RuleEngine:
    def __init__(self, detectors: Dict[str, Detector]) -> None
    def load_rules(self, rules: List[Dict]) -> List[Rule]
    def match_rules(self, page_type: str, rules: List[Rule]) -> List[Rule]
    def execute_rule(self, rule: Rule, context: PageContext) -> DetectionResult
    def execute_all(self, rules: List[Rule], context: PageContext) -> List[DetectionResult]
```

### 2.4 detectors/selector_detector.py - CSS Selector Detector

**Responsibility**: Detect page element existence through CSS selectors

**Key Functions**:
```python
class SelectorDetector:
    def detect(self, selector: str, page_source: str, browser: BrowserManager) -> DetectionResult
    def find_all_matches(self, selector: str, browser: BrowserManager) -> List[WebElement]
    def validate_selector(self, selector: str) -> bool
```

### 2.5 detectors/keyword_detector.py - Keyword Detector

**Responsibility**: Detect keywords or text patterns in page content

**Key Functions**:
```python
class KeywordDetector:
    def detect(self, keyword: str, page_source: str, case_sensitive: bool = False) -> DetectionResult
    def detect_pattern(self, pattern: str, page_source: str, regex: bool = False) -> DetectionResult
    def find_all_occurrences(self, keyword: str, page_source: str) -> List[MatchLocation]
```

### 2.6 detectors/network_detector.py - Network Request Detector

**Responsibility**: Detect specific URLs, parameters, or response content in network requests

**Key Functions**:
```python
class NetworkDetector:
    def detect(self, url_pattern: str, requests: List[NetworkRequest], 
               method: str = None, params: Dict = None) -> DetectionResult
    def detect_response_content(self, pattern: str, requests: List[NetworkRequest]) -> DetectionResult
    def filter_requests(self, requests: List[NetworkRequest], 
                       filters: Dict[str, Any]) -> List[NetworkRequest]
```

### 2.7 data/merchant_loader.py - Merchant Data Loader

**Responsibility**: Load merchant information from CSV files, validate data format

**Key Functions**:
```python
class MerchantLoader:
    def load(self, csv_path: str) -> List[Merchant]
    def validate(self, merchant: Merchant) -> bool
    def filter_by_status(self, merchants: List[Merchant], status: str) -> List[Merchant]
```

### 2.8 data/rule_loader.py - Rule Configuration Loader

**Responsibility**: Load rule configurations from YAML files, parse and validate rule format

**Key Functions**:
```python
class RuleLoader:
    def load_from_file(self, file_path: str) -> List[Rule]
    def load_from_directory(self, dir_path: str) -> List[Rule]
    def validate_rule(self, rule: Dict) -> Tuple[bool, List[str]]
    def parse_rule(self, rule_dict: Dict) -> Rule
```

### 2.9 report/report_generator.py - Report Generator

**Responsibility**: Aggregate audit results into JSON reports, including statistics

**Key Functions**:
```python
class ReportGenerator:
    def generate(self, results: List[AuditResult], output_path: str) -> str
    def create_summary(self, results: List[AuditResult]) -> Dict[str, Any]
    def format_result(self, result: AuditResult) -> Dict[str, Any]
    def export_json(self, data: Dict, file_path: str) -> bool
```

### 2.10 report/screenshot_manager.py - Screenshot Manager

**Responsibility**: Manage screenshot files, generate unique filenames, clean up old screenshots

**Key Functions**:
```python
class ScreenshotManager:
    def __init__(self, base_dir: str) -> None
    def generate_path(self, merchant_id: str, page_type: str, rule_id: str) -> str
    def save(self, screenshot_data: bytes, file_path: str) -> bool
    def cleanup_old_screenshots(self, days: int = 7) -> int
```

### 2.11 utils/logger.py - Logging Utility

**Responsibility**: Unified log format, support different log levels

**Key Functions**:
```python
class Logger:
    def setup(self, log_level: str, log_file: str = None) -> None
    def info(self, message: str, **kwargs) -> None
    def warning(self, message: str, **kwargs) -> None
    def error(self, message: str, **kwargs) -> None
    def debug(self, message: str, **kwargs) -> None
```

### 2.12 utils/validators.py - Data Validation Utility

**Responsibility**: Validate URLs, selectors, configurations, and other data validity

**Key Functions**:
```python
class Validators:
    @staticmethod
    def validate_url(url: str) -> bool
    @staticmethod
    def validate_selector(selector: str) -> bool
    @staticmethod
    def validate_merchant_data(data: Dict) -> Tuple[bool, List[str]]
    @staticmethod
    def validate_rule_config(config: Dict) -> Tuple[bool, List[str]]
```

## 3. merchant_registry.csv Field Definitions

```csv
merchant_id,merchant_name,base_url,checkout_url,product_url,cart_url,status,priority,notes
```

**Field Descriptions**:

| Field Name | Type | Required | Description | Example |
|------------|------|----------|-------------|---------|
| merchant_id | String | Yes | Unique merchant identifier | MERCHANT_001 |
| merchant_name | String | Yes | Merchant name | Example Store |
| base_url | String | Yes | Merchant website base URL | https://example.com |
| checkout_url | String | No | Checkout page URL (full or relative path) | /checkout or https://example.com/checkout |
| product_url | String | No | Product page URL (full or relative path) | /product/123 or https://example.com/product/123 |
| cart_url | String | No | Cart page URL (full or relative path) | /cart or https://example.com/cart |
| status | String | Yes | Merchant status (active/inactive/testing) | active |
| priority | Integer | No | Audit priority (1-10, higher number = higher priority) | 5 |
| notes | String | No | Notes | Test merchant, needs special handling |

**Example Data**:
```csv
merchant_id,merchant_name,base_url,checkout_url,product_url,cart_url,status,priority,notes
MERCHANT_001,Example Store,https://example.com,/checkout,/product/123,/cart,active,8,Main production store
MERCHANT_002,Test Store,https://test.example.com,/checkout,/products,/cart,testing,3,Development environment
```

## 4. Rule Configuration (YAML) Examples

### 4.1 Rule Configuration Structure

```yaml
rules:
  - rule_id: "CHECKOUT_001"
    description: "Detect if checkout page contains Klarna payment button"
    severity: "high"
    page_type: "checkout"
    detection:
      type: "selector"
      selector: "button[data-klarna]"
      expected: true
      timeout: 5
    
  - rule_id: "CHECKOUT_002"
    description: "Detect if checkout page contains Klarna brand identifier"
    severity: "medium"
    page_type: "checkout"
    detection:
      type: "keyword"
      keyword: "Klarna"
      case_sensitive: false
      expected: true
      context: "payment_methods"
    
  - rule_id: "CHECKOUT_003"
    description: "Detect if Klarna API request is initiated"
    severity: "high"
    page_type: "checkout"
    detection:
      type: "network"
      url_pattern: ".*klarna.*"
      method: "GET"
      expected: true
      response_check:
        status_code: 200
        content_pattern: ".*success.*"
    
  - rule_id: "PRODUCT_001"
    description: "Detect if product page displays Klarna installment option"
    severity: "medium"
    page_type: "product"
    detection:
      type: "selector"
      selector: ".klarna-widget, [data-klarna-widget]"
      expected: true
      multiple: true
    
  - rule_id: "CART_001"
    description: "Detect if cart page contains Klarna payment option"
    severity: "high"
    page_type: "cart"
    detection:
      type: "selector"
      selector: "input[value*='klarna'], select option[value*='klarna']"
      expected: true
```

### 4.2 Rule Field Descriptions

| Field Name | Type | Required | Description | Allowed Values |
|------------|------|----------|-------------|----------------|
| rule_id | String | Yes | Unique rule identifier | Any string |
| description | String | Yes | Rule description | Any string |
| severity | String | Yes | Severity level | high/medium/low |
| page_type | String | Yes | Applicable page type | checkout/product/cart/all |
| detection | Object | Yes | Detection configuration | See below |
| enabled | Boolean | No | Whether enabled (default true) | true/false |

**detection Object Fields**:

- **type**: Detection type (selector/keyword/network)
- **selector**: CSS selector (required when type=selector)
- **keyword**: Keyword (required when type=keyword)
- **url_pattern**: URL pattern (required when type=network)
- **expected**: Expected result (true/false)
- **timeout**: Timeout in seconds (default 5)
- **case_sensitive**: Case sensitive (keyword type, default false)
- **method**: HTTP method (network type, optional)
- **multiple**: Allow multiple matches (selector type, default false)
- **response_check**: Response check configuration (network type, optional)

## 5. JSON Report Schema

### 5.1 Complete Report Structure

```json
{
  "audit_metadata": {
    "audit_id": "AUDIT_20240101_120000",
    "timestamp": "2024-01-01T12:00:00Z",
    "version": "1.0.0",
    "total_merchants": 10,
    "total_rules": 15,
    "duration_seconds": 1250.5
  },
  "summary": {
    "total_merchants_audited": 10,
    "total_merchants_passed": 7,
    "total_merchants_failed": 3,
    "total_issues_found": 12,
    "issues_by_severity": {
      "high": 5,
      "medium": 4,
      "low": 3
    },
    "issues_by_page_type": {
      "checkout": 8,
      "product": 3,
      "cart": 1
    }
  },
  "merchants": [
    {
      "merchant_id": "MERCHANT_001",
      "merchant_name": "Example Store",
      "base_url": "https://example.com",
      "audit_status": "completed",
      "audit_timestamp": "2024-01-01T12:05:30Z",
      "total_issues": 2,
      "passed_rules": 8,
      "failed_rules": 2,
      "issues": [
        {
          "rule_id": "CHECKOUT_001",
          "rule_description": "Detect if checkout page contains Klarna payment button",
          "severity": "high",
          "page_type": "checkout",
          "status": "failed",
          "expected": true,
          "actual": false,
          "confidence": 0.95,
          "evidence": {
            "screenshot_path": "screenshots/MERCHANT_001_checkout_CHECKOUT_001_20240101_120530.png",
            "matched_selectors": [],
            "url": "https://example.com/checkout",
            "timestamp": "2024-01-01T12:05:30Z",
            "page_source_snippet": "<html>...</html>",
            "network_requests": [
              {
                "url": "https://example.com/api/payment",
                "method": "GET",
                "status_code": 200,
                "timestamp": "2024-01-01T12:05:31Z"
              }
            ]
          },
          "message": "Expected Klarna payment button not found on checkout page"
        }
      ]
    }
  ]
}
```

### 5.2 Schema Field Descriptions

**audit_metadata**:
- `audit_id`: Unique audit session ID
- `timestamp`: Audit start time (ISO 8601 format)
- `version`: Report format version
- `total_merchants`: Total number of merchants audited
- `total_rules`: Total number of rules executed
- `duration_seconds`: Total audit duration in seconds

**summary**:
- `total_merchants_audited`: Number of merchants audited
- `total_merchants_passed`: Number of merchants that passed audit
- `total_merchants_failed`: Number of merchants that failed audit
- `total_issues_found`: Total number of issues found
- `issues_by_severity`: Number of issues by severity level
- `issues_by_page_type`: Number of issues by page type

**merchants[].issues[].evidence**:
- `screenshot_path`: Screenshot file path (relative path)
- `matched_selectors`: List of matched selectors (selector detection type)
- `url`: Page URL at detection time
- `timestamp`: Detection timestamp (ISO 8601 format)
- `confidence`: Detection confidence (0.0-1.0)
- `page_source_snippet`: Page source snippet (optional, for debugging)
- `network_requests`: List of related network requests (network detection type)

### 5.3 Data Type Definitions

```python
# Pseudo-code type definitions
AuditReport = {
    audit_metadata: AuditMetadata,
    summary: Summary,
    merchants: List[MerchantResult]
}

MerchantResult = {
    merchant_id: str,
    merchant_name: str,
    base_url: str,
    audit_status: str,  # "completed" | "failed" | "skipped"
    audit_timestamp: str,  # ISO 8601
    total_issues: int,
    passed_rules: int,
    failed_rules: int,
    issues: List[Issue]
}

Issue = {
    rule_id: str,
    rule_description: str,
    severity: str,  # "high" | "medium" | "low"
    page_type: str,  # "checkout" | "product" | "cart"
    status: str,  # "passed" | "failed"
    expected: bool,
    actual: bool,
    confidence: float,  # 0.0-1.0
    evidence: Evidence,
    message: str
}

Evidence = {
    screenshot_path: str,
    matched_selectors: List[str],
    url: str,
    timestamp: str,  # ISO 8601
    confidence: float,
    page_source_snippet: Optional[str],
    network_requests: Optional[List[NetworkRequest]]
}
```

## 6. Data Models

### 6.1 Merchant Model

```python
@dataclass
class Merchant:
    merchant_id: str
    merchant_name: str
    base_url: str
    checkout_url: Optional[str]
    product_url: Optional[str]
    cart_url: Optional[str]
    status: str  # "active" | "inactive" | "testing"
    priority: int  # 1-10
    notes: Optional[str]
```

### 6.2 Rule Model

```python
@dataclass
class Rule:
    rule_id: str
    description: str
    severity: str  # "high" | "medium" | "low"
    page_type: str  # "checkout" | "product" | "cart" | "all"
    detection: DetectionConfig
    enabled: bool = True

@dataclass
class DetectionConfig:
    type: str  # "selector" | "keyword" | "network"
    expected: bool
    timeout: int = 5
    # Selector specific
    selector: Optional[str] = None
    multiple: bool = False
    # Keyword specific
    keyword: Optional[str] = None
    case_sensitive: bool = False
    regex: bool = False
    # Network specific
    url_pattern: Optional[str] = None
    method: Optional[str] = None
    response_check: Optional[Dict] = None
```

### 6.3 DetectionResult Model

```python
@dataclass
class DetectionResult:
    rule_id: str
    passed: bool
    expected: bool
    actual: bool
    confidence: float
    evidence: Evidence
    message: str
    timestamp: str
```

## 7. Configuration Examples

### 7.1 browser_config.yaml

```yaml
browser:
  type: "chrome"  # chrome | firefox | edge
  headless: true
  window_size:
    width: 1920
    height: 1080
  timeout:
    page_load: 30
    element_wait: 10
  options:
    - "--no-sandbox"
    - "--disable-dev-shm-usage"
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
```

### 7.2 audit_config.yaml

```yaml
audit:
  parallel_execution: false
  max_workers: 3
  retry_failed: true
  max_retries: 2
  screenshot:
    enabled: true
    format: "png"
    quality: 90
  report:
    format: "json"
    output_dir: "reports"
    include_page_source: false
  filters:
    merchant_status: ["active"]
    rule_severity: ["high", "medium"]
```

---

## Design Notes

1. **Modular Design**: Clear responsibilities for each module, easy to test and maintain
2. **Extensibility**: Detectors use strategy pattern, easy to add new detection types
3. **Configuration-Driven**: Rules and configurations managed through YAML/CSV, no code changes needed
4. **Complete Evidence Chain**: Reports include screenshots, selectors, URLs, and other complete evidence
5. **Type Safety**: Use dataclass to define data models, provide type hints
6. **Error Handling**: Each module should include appropriate error handling and logging
