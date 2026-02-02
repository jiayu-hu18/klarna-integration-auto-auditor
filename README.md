# Klarna Integration Auto Auditor

An automated auditing tool for Klarna integration (Phase 0: single merchant).

## Installation

1. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate    # Windows
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

### Phase 0: Single Merchant Audit

Default merchant is **jula.se**; use `--merchant` to audit another site (e.g. aliexpress.com, shein.com).

```bash
python -m auditor.run --out-dir out
python -m auditor.run --out-dir out --merchant https://www.aliexpress.com
python -m auditor.run --out-dir out --merchant https://www.shein.com
```

**Command line options:**
- `--out-dir` (required): Output directory for reports and screenshots
- `--merchant`: Merchant URL or domain (default: https://www.jula.se)
- `--headless`: Run headless (default: true)
- `--headed`: Run with visible browser (overrides `--headless`)
- `--slowmo`: Delay in ms (e.g. 300 for debugging)
- `--locale`: Browser locale (default: guessed from merchant URL)

**Examples:**
```bash
# Headless
python -m auditor.run --out-dir out

# Visible browser + slowmo (debugging)
python -m auditor.run --out-dir out --headed --slowmo 300
```

**Output:**
- JSON report: `out/<merchant>/report.json`
- Screenshots: `out/<merchant>/*.png`, `out/<merchant>/debug/*.png` (footer payments section, PDP, etc.)

**Checks:**
1. **FOOTER_KLARNA_LOGO** – Klarna in footer “Pay with” / payment methods area. Scrolls to true bottom (wheel) to trigger lazy-loaded footer, clears overlays (ESC + safe close + CSS-hide large fixed/sticky), brings footer into view, then freezes scroll; locates payments section by text (Pay with / Payment methods / We accept), takes element screenshot of that section only, runs multi-template match with template-specific aspect-ratio filter. Evidence: `footer_payments_section_attempt*.png` (must visibly show Klarna). No full-viewport match (avoids false positive on product grid “Choice”).
2. **PDP_OSM** – Klarna On-Site Messaging in product scope on PDP
3. **CART_KLARNA** – Klarna on cart page (add-to-cart flow)
4. **CHECKOUT_PAYMENT_POSITION** – Klarna in payment methods and position

**Behaviour:**
- Cookie consent is dismissed (e.g. “Acceptera alla cookies” on jula.se)
- For jula.se, PDP is auto-picked from `/erbjudanden/` catalog links if no PDP URL is set
- Locale is inferred from domain (jula.se → sv-SE, humac.dk → da-DK, etc.)

See [README_PHASE0.md](README_PHASE0.md) for Phase 0 details.

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
- ✅ Single merchant audit (default: jula.se; `--merchant` for aliexpress.com, shein.com, etc.)
- ✅ Footer check: scroll-to-true-bottom (wheel), overlay clear (ESC + safe close + CSS-hide), bring footer into view, freeze scroll, locate “Pay with” section, element screenshot only, multi-template match + aspect-ratio filter (wordmark ≥1.8, pink ≥1.15); evidence = payments section screenshot
- ✅ PDP OSM check scoped to product area; auto PDP from home for jula.se (/erbjudanden/ + catalog links)
- ✅ Cookie consent dismissal; overlay clear (ESC + safe close + hide large fixed/sticky)
- ✅ Locale from URL (sv-SE, da-DK, en-US, etc.)
- ✅ Screenshot capture and JSON report; 10s timeouts; error isolation

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
