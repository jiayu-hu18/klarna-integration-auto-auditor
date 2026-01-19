# Klarna Integration Auto Auditor

An automated auditing tool for Klarna integration, designed for team collaboration.

## Installation

1. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

## Usage

### Phase 0: Single Merchant Audit (Current)

Run Phase 0 audit for a single merchant (humac.dk):

```bash
python -m auditor.run --out-dir out --headless true
```

**Command Line Options:**
- `--out-dir` (required): Output directory for reports and screenshots
- `--headless` (optional): Run browser in headless mode (default: `true`)
- `--slowmo` (optional): Slow down operations by milliseconds (for debugging)
- `--locale` (optional): Browser locale (default: `da-DK`)

**Example:**
```bash
# Run with visible browser (for debugging)
python -m auditor.run --out-dir out --headless false --slowmo 200
```

**Output:**
- JSON Report: `out/humac.dk/report.json`
- Screenshots: `out/humac.dk/*.png` (footer, pdp_osm, cart, checkout_payment)

**Checks Performed:**
1. **FOOTER_KLARNA_LOGO** - Detects Klarna logo in footer
2. **PDP_OSM** - Detects Klarna On-Site Messaging on product page
3. **CART_KLARNA** - Detects Klarna in cart page
4. **CHECKOUT_PAYMENT_POSITION** - Detects Klarna payment method position

See [README_PHASE0.md](README_PHASE0.md) for detailed Phase 0 documentation.

### Batch Audit (Future)

For batch processing with CSV merchant registry:

```bash
python -m app.run --input data/merchant_registry.csv --out out/
```

## Project Structure

```
klarna-integration-auto-auditor/
├── auditor/              # Phase 0 single merchant audit
│   ├── run.py           # CLI entry point
│   ├── checks/          # Audit checks
│   ├── navigator.py     # Page navigation
│   ├── screenshot.py   # Screenshot management
│   └── report.py        # JSON report generation
├── app/                 # Batch audit (existing)
├── data/
│   └── addresses/       # Test addresses for different countries
├── tests/               # Test files
└── out/                 # Output directory
```

## Test Addresses

Test addresses are stored in `data/addresses/addresses.json`. You can manually edit this file to add/update addresses for different countries. The system uses Klarna-approved test data from [Klarna's official documentation](https://docs.klarna.com/resources/developer-tools/sample-data/sample-customer-data/).

**Example:**
```json
{
  "DK": {
    "first_name": "Test",
    "last_name": "Person-dk",
    "email": "customer@email.dk",
    "phone": "+4542555628",
    "street": "Dantes Plads 7",
    "postal_code": "1556",
    "city": "København Ø",
    "country": "DK"
  }
}
```

## Running Tests

```bash
pytest tests/
```

## Features

### Phase 0 (Current)
- ✅ Single merchant audit (humac.dk)
- ✅ 4 automatic checks with error isolation
- ✅ Screenshot capture for each check
- ✅ JSON report generation
- ✅ Optimized timeouts (10s max per operation)
- ✅ Cookie banner auto-handling
- ✅ Iframe support for detection

### Batch Audit (Future)
- ✅ Reads merchant registry from CSV
- ✅ Uses Playwright to visit merchant homepages
- ✅ Detects Klarna logo in footer
- ✅ Generates JSON reports with evidence
- ✅ Timeout and retry mechanisms
- ✅ Exception isolation

## Documentation

- [README_PHASE0.md](README_PHASE0.md) - Phase 0 detailed documentation
- [DESIGN.md](DESIGN.md) - Project design document
- [PHASE0_DESIGN.md](PHASE0_DESIGN.md) - Phase 0 design document

## License

TBD
